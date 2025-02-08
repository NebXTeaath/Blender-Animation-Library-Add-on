# Blender Animation Library Add-on

[![License: GPL v2 or later](https://img.shields.io/badge/License-GPL_v2%2B-blue.svg)](https://www.gnu.org/licenses/gpl-2.0.html)

## Overview

The **Blender Animation Library Add-on** streamlines the process of saving, applying, and managing animations in Blender. It makes it easier to reuse motion data efficiently by allowing you to:

- **Save Animations:**  
  Export keyframe data for either selected bones (in Pose Mode) or all bones (in Object Mode). The add-on creates a new action based on your current animation, purges any previously cached versions if needed, and saves the asset along with an accompanying thumbnail.

- **Load & Apply Animations:**  
  Browse your saved animations and apply them to compatible rigs. When applied, keyframes are shifted so that the first keyframe snaps to the current timeline playhead.

- **Manage Animations:**  
  Search your animation library with a built-in search bar and use compact icon buttons to quickly apply or delete assets.

> **Current Issue:**  
> Although the add-on correctly generates and saves thumbnail images next to the exported `.blend` files, these thumbnails do not display in Blender’s UI. Any insights or fixes to resolve this issue would be greatly appreciated!

## Features

- **Flexible Export Options:**  
  - **Pose Mode:** Exports only the channels for selected bones if any are selected.  
  - **Object Mode:** Exports the entire animation for the selected object.
- **Intelligent Keyframe Pasting:**  
  Automatically adjusts keyframes so that the first keyframe of the exported animation snaps to the timeline cursor.
- **Compact UI:**  
  A neat interface with a searchable Animation Browser and icon-based Apply and Delete actions.
- **File Management:**  
  Save assets to a dedicated, project-specific library folder with automatic thumbnail generation.

## Demo Video

Watch the demo video below to see the add-on in action:

[![Demo Video](https://github.com/user-attachments/assets/72dd3702-0d44-48d5-a101-bbff676e006a)](https://github.com/user-attachments/assets/60991e94-785f-483d-8ccb-b10344dee34d)

## How to Use

1. **Install the Add-on:**  
   Open Blender’s Preferences > Add-ons > Install and select the Python script.

2. **Set Library Path:**  
   In the Animation Library panel, specify the folder where you want to save your animations (editable per project).

3. **Save Animations:**  
   - Enter a unique name in the text field.
   - Click **"Save Animation"** to export the current animation.  
     - In Pose Mode, if bones are selected, only those bones’ keyframes are exported.
     - In Object Mode, all keyframes are exported.
4. **Browse & Apply:**  
   Use the Animation Browser to search, apply, or delete animations.
5. **Feedback:**  
   Informative messages are displayed after each operation (e.g., "Exported animation for selected bones." or "Applied animation: X at playhead Y with blend Z").

## Contributing

Contributions are welcome! If you have suggestions or fixes—especially regarding the missing thumbnail previews—please open an issue or submit a pull request.

## License

This project is licensed under the [GPL-2.0-or-later](https://www.gnu.org/licenses/gpl-2.0.html) license.

---

*Thank you for checking out the Blender Animation Library Add-on!*
