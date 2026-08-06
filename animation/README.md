# Wallet V2 product animation

This scene is built from the exact solid bodies in `../walletv2.FCStd`:

- main wallet shell
- front slider, drive cam, and swing arm
- rear hinged door
- modeled credit card, duplicated for the five-card cascade

The final cut is a 14-second, 1080 x 1080, 30 fps H.264 product film. It opens
with a front hero shot, animates the arm and five cards, resets the mechanism,
orbits to the rear, opens the door, and loads a folded banknote bundle and five
coins into the compartment. The door closes and the camera returns to the exact
opening transform for a seamless loop.

## Loading the compartment without collisions

The rear cavity measures 54.5 x 98.8 mm but is only **4.45 mm deep**, between
its inner face and the shut door. That depth, and the 20.5-31.65 mm Australian
coin diameters modeled at scene scale, drives the whole loading sequence:

- **Coins lie in a single layer.** Five true-scale coins plus the cash bundle
  would need 77% packing density in the space below the notes, which no
  arrangement achieves. Four coins lie flat with at least 0.75 mm between them
  and the walls. The 2.0 mm ten-cent piece is the only coin thin enough to rest
  on another and still clear the shut door, so it sits on the fifty.
- **The cash is thicker than it looks.** Each note is tilted about Z, which
  leans its 48 mm length into the depth axis, making the bundle 3.48 mm rather
  than the 1.7 mm of stacked paper. It claims most of the depth in the band
  above the coins.
- **The open door blocks its own doorway.** Swung back, the hinge side lies
  across the left edge of the mouth out to x=-0.2466, so the whole load is
  packed clear of that side rather than centred in the cavity.
- **Nothing travels sideways inside the wallet.** Each item tumbles only on its
  opening leg, well outside the shell. By the drift key it is lined up over its
  own resting place and flat, and everything after that moves along -Y alone
  while spinning about its own axis. A descent that never travels sideways
  cannot sweep through the shell rim, the open door, or anything already
  settled, and because the resting footprints do not overlap, neither do the
  columns the items come down in. Arrivals are spaced seven frames apart so
  only one item is ever working its way down the funnel.

`check_collisions.py` verifies this the hard way, intersecting the evaluated
meshes pair by pair on every frame of the film.

The arm, cam, and internal slider share the same 83.282-degree pivot motion,
the contact angle solved from the curved recessed-area profile.
`analyze_linkage.py` clips the real slider mesh against its five contact lanes;
the resulting card lifts are 6.0, 13.0, 20.0, 27.0, and 34.0 mm. Those curves
are sampled on every rendered frame so the cards remain linked to the slider.
The material direction is deliberately restrained: carbon black shell,
graphite mechanism, and muted realistic card colours.

## Files

- `output/wallet_v2_product_film.mp4` - final encoded film
- `output/wallet_v2_animation.blend` - editable Blender scene
- `output/preview_001.png` - closed hero still
- `output/preview_112.png` - card cascade still
- `output/preview_linkage_mid.png` - mid-stroke linkage still
- `output/preview_292.png` - coins squared up at the mouth still
- `output/preview_315.png` - part-loaded compartment still
- `output/preview_336.png` - loaded-compartment still
- `output/preview_365.png` - rear door closed still
- `output/preview_420.png` - matching loop frame
- `output/contact_sheet.png` - one-frame-per-second QA overview
- `check_collisions.py` - per-frame mesh intersection test for the load

## Rebuild

From the repository root in PowerShell:

```powershell
& 'C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe' animation\export_parts.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python animation\build_scene.py -- --preview
```

For a full lossless frame render, replace `--preview` with `--video`. This
Blender build lists FFMPEG among the image formats but rejects it at
assignment, so the movie is encoded separately from the rendered sequence:

```powershell
ffmpeg -y -framerate 30 -i animation\output\frames\frame_%04d.png -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -movflags +faststart animation\output\wallet_v2_product_film.mp4
```

To confirm nothing intersects, run the checker over the whole film. It reports
every pair of meshes that overlap and on which frames, and exits non-zero if it
finds any:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup animation\output\wallet_v2_animation.blend --python animation\check_collisions.py -- --start 1 --end 420
```
