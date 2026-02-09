# Sync with GitHub Desktop

This folder is a **fresh Git repo** (no commits yet). Use GitHub Desktop to add it and publish.

## Steps

1. Open **GitHub Desktop**.
2. **File → Add local repository** (or **Add → Add Existing Repository**).
3. Click **Choose...** and select **this folder** (`clawd`).
4. Desktop will show the repo with many **untracked** files. In the left sidebar, tick **all** the files you want to commit (or leave all selected for the first commit).
5. Write a commit message (e.g. *Initial commit*) and click **Commit to master**.
6. Click **Publish repository** (top right). Choose your GitHub account and:
   - **Name:** e.g. `ComputerVision` or `clawd`.
   - **Keep this code private** if you want.
   - If you already have an empty repo on GitHub, you may need to add it as a remote and push instead of "Publish" (Desktop will guide you).
7. After that, use **Push** / **Pull** in Desktop to stay in sync.

**.gitignore** is already set: large training data, `.env`, and caches are not committed. Only code and config will be synced.
