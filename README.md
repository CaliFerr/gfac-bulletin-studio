# GFAC Bulletin Studio

GFAC Bulletin Studio is a Windows desktop app for three main jobs:

- Build and edit a church program CSV
- Generate the bulletin program PDF
- Generate PowerPoint slides and lower thirds from that CSV

## Install

Use your project Python and install the requirements:

```powershell
python -m pip install -r requirements.txt
```

## Run The App

```powershell
python main.py
```

## Main Tools

### 1. Create Program

Use `Create Program` on the first screen when you want to make a new CSV from scratch.

What it does:

- Opens the Program Maker
- Starts with the three fixed sections:
  - `Filipino Service`
  - `Sabbath School`
  - `Hour Of Worship`
- Lets you add rows, remove rows, reorder rows, and save the CSV

Tips:

- Double-click a section time to edit it
- Use `Save` to write the CSV
- Use `Save + Use` to save it and jump straight into the tools page

### 2. Import CSV

Use `Import CSV` when you already have a CSV file and want to work from it.

What it does:

- Loads the CSV into the app
- Prefills the default output locations
- Opens the tools page

### 3. Edit CSV

On the tools page, use `Edit CSV` to reopen the current CSV in the editor popup.

What it does:

- Loads the active CSV into the Program Maker
- Lets you update rows and section times
- Saves changes back into the same file

### 4. Bulletin Maker

Use this to generate the program portion of the bulletin PDF.

What it expects:

- The current CSV
- A PDF output path

What it generates:

- The bulletin program layout based on your sectioned CSV

After success:

- The app opens the output location in File Explorer

### 5. Slides Generator

Use this to create PowerPoint slides from a template.

What it expects:

- The current CSV
- A selected `.pptx` template
- An output `.pptx` path

What it generates:

- A slide deck based on the current CSV rows and your template placeholders

Template notes:

- Use the gallery button to choose a template
- Imported templates are stored in the local `templates` folder
- Thumbnails are stored in the local `thumbnails` folder

After success:

- The app opens the output location in File Explorer

Important:

- Slide generation requires Microsoft PowerPoint on Windows

### 6. Lower Thirds

Use this to export lower-third PNGs from the current CSV.

What it expects:

- The current CSV
- An output folder

What it generates:

- `1920x1080` PNG lower thirds using the bundled design assets

After success:

- The app opens the output folder in File Explorer

## CSV Format

The app saves and reads this structure:

```csv
title,subheading,small_subheading
Filipino Service,9:00 am,
Opening Song,Hymn 350,Ang Pag Asa Ka ay Natatag
Opening Prayer,Seth Encontro,
Sabbath School,10:00 am,
Lesson Review,By Classes,Living With Each Other
Hour Of Worship,11:15 am,
Message,Sean Gasmen,Young, But Not Small!
```

Meaning:

- `title`: main item title
- `subheading`: usually the person name or subtitle
- `small_subheading`: optional extra line

The three section rows are used as section separators.

## Build A Windows App

This project includes a PowerShell build script for packaging with PyInstaller.

Run:

```powershell
.\build.ps1
```

If you want to force a specific Python:

```powershell
.\build.ps1 -PythonExe "C:\Path\To\python.exe"
```

Build output:

- The packaged app will be created in `dist\GFAC Bulletin Studio`

## Build A Single EXE

If you want one file instead of the normal app folder, use:

```powershell
.\build_onefile.ps1
```

Or with a specific Python:

```powershell
.\build_onefile.ps1 -PythonExe "C:\Path\To\python.exe"
```

One-file output:

- `dist\GFAC Bulletin Studio.exe`

Notes:

- One-file builds usually start slower
- The current one-folder build is still the safer option if you want the most reliable packaging

Included in the packaged build:

- `assets`
- `templates`
- `thumbnails`

## Notes

- This app is designed for Windows
- PowerPoint export depends on COM automation, so Microsoft PowerPoint must be installed
- Templates and thumbnails are stored locally beside the app/project
