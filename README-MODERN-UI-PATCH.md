# Modern UI patch — 3D Modern Periodic Table

This is an additive UI launcher for the existing Pygame CE application. It keeps the current `periods_&_blocks.py` renderer and `elements.json` dataset in place, and adds a refined HUD, selected/hovered cube edge glow, a subtle animated header accent, and keyboard-driven element search.

## Install

1. Download and extract this patch.
2. Copy `launch_modern.py` into the **root folder** of your existing repository, beside `periods_&_blocks.py` and `elements.json`.
3. From that repository folder, install the existing dependency if needed:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Start the enhanced interface:

   ```powershell
   python launch_modern.py
   ```

The existing `python "periods_&_blocks.py"` launch command remains available and unchanged.

## Controls

- Click the search box in the 3D table panel, or press `/`, then type an element name, symbol, or atomic number and press **Enter**.
- Drag over the table to rotate it.
- Use the mouse wheel to zoom, or scroll the element details panel.
- Press `R` to reset the 3D view.
- Press `Esc` to exit.

## Notes

- This patch does not alter chemistry data or replace the original renderer.
- `launch_modern.py` passed Python syntax compilation in the build environment. A full graphical runtime test was not possible here because Pygame CE and the rest of the repository were not locally mounted; install dependencies and test the launcher alongside the repository files before relying on it.
