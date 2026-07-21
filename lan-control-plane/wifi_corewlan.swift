import Foundation
import CoreWLAN
import CoreLocation

func bandString(_ ch: CWChannel?) -> String {
    guard let ch = ch else { return "" }
    switch ch.channelBand {
    case .band2GHz: return "2GHz"
    case .band5GHz: return "5GHz"
    case .band6GHz: return "6GHz"
    default: return ""
    }
}

func securityString(_ n: CWNetwork) -> String {
    if n.supportsSecurity(.wpa3Enterprise) { return "WPA3 Enterprise" }
    if n.supportsSecurity(.wpa3Personal) { return "WPA3 Personal" }
    if n.supportsSecurity(.wpa3Transition) { return "WPA2/WPA3 Personal" }
    if n.supportsSecurity(.wpa2Enterprise) { return "WPA2 Enterprise" }
    if n.supportsSecurity(.wpa2Personal) { return "WPA2 Personal" }
    if n.supportsSecurity(.wpaPersonalMixed) { return "WPA/WPA2 Personal" }
    if n.supportsSecurity(.wpaPersonal) { return "WPA Personal" }
    if n.supportsSecurity(.WEP) { return "WEP" }
    if n.supportsSecurity(.none) { return "None" }
    return "unknown"
}

var out: [String: Any] = [
    "location_services_enabled": CLLocationManager.locationServicesEnabled(),
]

let client = CWWiFiClient.shared()
guard let iface = client.interface() else {
    out["error"] = "no Wi-Fi interface"
    print(String(data: try! JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
    exit(0)
}
let current = iface.ssid()
out["interface"] = iface.interfaceName ?? ""
out["current_ssid"] = current ?? NSNull()

do {
    let networks = try iface.scanForNetworks(withSSID: nil)
    var arr: [[String: Any]] = []
    for n in networks {
        let ssid = n.ssid
        arr.append([
            "ssid": ssid ?? NSNull(),
            "bssid": n.bssid ?? NSNull(),
            "rssi": n.rssiValue,
            "noise": n.noiseMeasurement,
            "channel": n.wlanChannel?.channelNumber ?? NSNull(),
            "band": bandString(n.wlanChannel),
            "security": securityString(n),
            "connected": (ssid != nil && current != nil && ssid == current),
        ])
    }
    out["count"] = arr.count
    out["networks"] = arr
    out["redacted"] = arr.contains { ($0["ssid"] as? String) == nil }
} catch {
    out["scan_error"] = "\(error)"
}

let data = try! JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .sortedKeys])
print(String(data: data, encoding: .utf8)!)
