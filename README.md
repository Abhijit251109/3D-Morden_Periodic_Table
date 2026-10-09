# Rotatable 3D Periodic Table

A desktop periodic table built with Pygame CE. Element tiles are rendered as
perspective-projected 3D cubes and can be rotated with the mouse. The app opens
in fullscreen mode; press `Esc` to exit.

## Run on Windows

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe "periods_&_blocks.py"
```

## Controls

- Drag the table to rotate it in 3D.
- Use the mouse wheel over the table to zoom.
- Click an element to select it and inspect its reported properties.
- The information panel shows an animated Bohr-style atom for the selected
  neutral element, using its electron-shell populations from the bundled data.
- Use the mouse wheel over the information panel to scroll through the data.
- Press `R` or click **Reset View** to reset the camera; press `Esc` to quit.

The lanthanoid and actinoid series occupy periods 6 and 7 in successive 3D
depth layers behind group 3. Each series recedes in atomic-number order along a
straight line (for example, La, Ce, …, Yb, Lu, and Ac, Th, …, No, Lr), rather
than shifting diagonally across the table. The default camera angle shows the
depth ordering; drag to rotate the table further.

## Element data

`elements.json` bundles records for atomic numbers 1–118. Element properties
and table coordinates are based on
[Periodic-Table-JSON](https://github.com/Bowserinator/Periodic-Table-JSON);
each record retains its individual source URL. The dataset's prose summaries
and image assets are not bundled.
