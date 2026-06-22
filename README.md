# 📑 Shehadat Generator

An automated Python tool equipped with a graphical user interface (GUI) to generate, format,
and rank student transcript certificates (**Shehadat**) from Excel spreadsheets.
Designed specifically with native **Right-to-Left (RTL) Arabic text support**, dynamic table scaling, and multi-term tracking.

---

## ✨ Features

* **User-Friendly GUI**: Built with `tkinter`, featuring directory browsers, term selection checkboxes, and a real-time console log stream.
* **Arabic Text Support**: Correctly handles Right-to-Left formatting and Arabic letter shaping using `arabic_reshaper` and `python-bidi`.
* **Smart Table Autoscaling**: Dynamically shrinks table font sizes step-by-step to guarantee that wide grade tables fit perfectly within standard landscape A4 margins.
* **Automated Merit Ranking**: Automatically tracks individual student percentages across selected terms (including optional Term 3 bonuses) and ranks the final merged PDF from highest score to lowest score.
* **Custom Layout Decoration**: Draws standard church/school header metadata, borders, and student ID cards directly onto the PDF canvas background layer.

---

## 🛠️ Requirements & Installation

Make sure you have Python 3.x installed. You will need a standard Arabic font file (like `times.ttf`) and an optional school logo template (`talmaza_logo.jpg`) in your project root folder.

### 1. Clone the repository
```bash
git clone https://github.com/bish0ymagdy/Shehadat-Generator.git
```

### 2. Install Dependencies
Install the required packages using `pip`:
```bash
pip install reportlab pandas openpyxl arabic-reshaper python-bidi pypdf2
```

### 3. Turn it to a 
Install the required packages using `pip`:
```bash
pip install pyinstaller
pyinstaller  --onefile --windowed --icon=icon.ico --add-data "times.ttf;." script_name --name="the_name_u_want"
```
---

## 📂 Expected File Structure

For the script to parse data properly, your workspace and source directories should look like this:

```text
📂 shehadat-generator/
│
├── 📄 main.py               # The main python script provided
├── 🔤 times.ttf             # Required for Arabic Font metrics
├── 🖼️ talmaza_logo.jpg      # Header Logo image for the certificate
│
└── 📂 Classes/              # Default folder containing your source data
    ├── 📊 الفصل الاول المستوي الأول.xlsx
    └── 📊 الفصل الثاني المستوي الثاني.xlsx
```

### Excel Sheet Guidelines
* **File Name**: The script parses the file name to extract the class and level (e.g., looks for the phrase `"المستوي"`).
* **Sheet Names**: Sheets should be named `Term_1`, `Term_2`, and `Term_3`.
* **Data Layout**:
    * **Row 0**: Header row containing course titles.
    * **Row 1**: Maximum possible grades (الدرجة الكلية) for each column.
    * **Column 0**: Student IDs.
    * **Column 1**: Student Names.
    * **Subsequent Columns**: Grade points. (If a column in `Term_3` is explicitly titled `bonus`, it is factored into the final ranking aggregation without altering base grade scales).

---

## 🚀 How to Use

1. Run the application:
   ```bash
   python main.py
   ```
2. **Select Folder**: Use the **Browse** button to point to the directory containing your `.xlsx` class files (Defaults to `.\Classes`).
3. **Select Terms**: Check or uncheck which terms (`Term_1`, `Term_2`, `Term_3`) you want included in the transcript generation.
4. **Click Generate**: The engine executes in a background thread to keep the window responsive. 
5. **View Output**: 
   * Temporary individual files pass through `.\single`.
   * The final consolidated class list PDFs (sorted by merit ranking) are exported to `.\Shehadat`.

---

## ⚙️ Core Logic Technical Details

* **Threaded Execution**: Prevents the Tkinter UI from freezing during heavy-duty PDF processing and merging.
* **Failing Flag Mechanics**: The application evaluates course headers. If a core spiritual column containing words like `"طقس"` or `"قبطي"` drops under 50% of the total allocated max value, it flags an explicit execution mark `X` meaning an update/re-test evaluation is required.
* **Stream Redirection**: Both `sys.stdout` and `sys.stderr` are bound to a custom `TextRedirector` class, forwarding terminal logs directly into the GUI's green-on-black scrolling execution console.
