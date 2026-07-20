"""Course compatibility shim for DeepLearning.AI / older Lamini notebooks.

`from llama import BasicModelRunner` was removed in lamini 3.x.
This local module (project-only) restores the old callable API on top of Lamini.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from lamini import Lamini


class BasicModelRunner(Lamini):
    """Deprecated course helper: ``runner(prompt)`` → ``Lamini.generate(prompt)``."""

    def __call__(
        self,
        prompt: Union[str, list],
        **kwargs: Any,
    ) -> Any:
        return self.generate(prompt, **kwargs)


__all__ = ["BasicModelRunner", "Lamini"]
