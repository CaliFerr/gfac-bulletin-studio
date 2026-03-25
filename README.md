# GFAC Bulletin And Slide Generator

This project generates:

- A two-column church bulletin PDF for the `PROGRAM` section
- A PowerPoint deck from a chosen template and CSV file

## Install

```powershell
& 'C:\Users\steak\AppData\Local\Programs\Python\Python313\python.exe' -m pip install -r requirements.txt
```

## CSV formats

Preferred bulletin format:

```csv
order,title,extra,name
1,Opening Song,Ang Pag Asa Ka ay Natatag,Himno 350
2,Opening Prayer,,Seth Encontro
```

Legacy slide-editor format also works:

```csv
title,subheading,small_subheading
Opening Song,Himno 350,Ang Pag Asa Ka ay Natatag
Opening Prayer,Seth Encontro,
```

Assumption for legacy files:

- `title` -> bulletin title
- `subheading` -> name
- `small_subheading` -> extra

## Generate The Bulletin PDF

```powershell
& 'C:\Users\steak\AppData\Local\Programs\Python\Python313\python.exe' main.py pdf .\sample_program.csv .\output\program.pdf
```

## Generate Slides

```powershell
& 'C:\Users\steak\AppData\Local\Programs\Python\Python313\python.exe' main.py slides .\sample_program.csv 'C:\path\to\template.pptx' .\output\program_slides.pptx
```

## Notes

- The PDF layout uses ReportLab with two real document columns on letter-size paper.
- The slide generator keeps the PowerPoint placeholder flow from your current app:
  - `[Title]`
  - `[Subheading]`
  - `[Smaller Subheading]`
- Slide generation requires Microsoft PowerPoint on Windows because it uses COM automation.
