# EasyDATI

**EasyDATI** is an application designed to streamline and secure the creation of structured datapacks for the **Palma PLM (Windchill)** system. It is tailored to support the DATI import process by offering an intuitive interface for managing primary and secondary content files, linking metadata, and preparing compliant data packages ready for integration.

---

## Key Features

* **Interactive Table Editor**: Modify documents, links, and metadata directly in a spreadsheet-like interface based on Tabulator.js with rich cell editors (text, dropdown, file picker, calendar, etc.).
* **Multi-file Upload & Parsing**: Drag-and-drop or bulk import files from ZIP archives or local storage; includes automatic parsing of associated metadata (CSV, Excel).
* **PDF Viewer Docking**: Inline PDF previews via a flexible docking layout to visually validate files linked to table rows.
* **IndexedDB Persistence**: Autosave your session locally with optional manual saving, ensuring recovery after reloads or crashes.
* **Custom File Bucket Logic**: Temporarily associates uploaded files with the rows they belong to, maintaining mapping through unique identifiers.
* **Import & Export Pipelines**: Full support for DATI-compatible export format with CSV normalization and ZIP packaging.
* **Data Validation**: Built-in validation for import structure, field presence, and file integrity.

---

## Technologies

EasyDATI uses a modern and robust tech stack:

* **Vite** – Ultra-fast frontend tooling and hot module replacement
* **React 18** – Reactive and component-driven UI
* **TypeScript** – Static type checking for reliability and tooling
* **Tailwind CSS** – Custom UI with utility-first styling
* **Tailwind Variants** – Class logic abstraction for styling variants
* **HeroUI** – React component library for inputs, buttons, layout controls
* **react-mosaic** – React component library for mosaic-style windows, used in our case to separate the PDF and the table view
* **JSZip** – ZIP file reading and generation
* **Papaparse** – Fast CSV parsing and export
* **IDB / async-mutex** – Safe asynchronous IndexedDB operations
* **Tabulator** – Spreadsheet-like table engine with custom formatters and editors

---

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/frontio-ai/vite-template.git
d cd vite-template
```

### Install Dependencies

```bash
npm install
```

Or with `pnpm`:

```bash
pnpm install
```

Ensure `.npmrc` includes:

```text
public-hoist-pattern[]=*@heroui/*
```

### Run the App

```bash
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## Project Structure

```text
├── public/                    # Static assets (icons, splash screen, etc.)
├── src/
│   ├── components/            # UI components (buttons, inputs, layout, viewers)
│   ├── features/              # Core features like table, import, export, validation
│   │   └── table/             # Tabulator setup, custom columns, editors
│   ├── layouts/               # Page layout wrappers
│   ├── pages/                 # Application routes: index, main app, etc.
│   ├── utils/                 # Utility functions: MIME, date formatting, etc.
│   ├── lib/                   # IndexedDB logic for persistent storage
│   └── App.tsx                # App root
├── index.html                 # HTML entry point
├── tsconfig.json              # TypeScript config
├── tailwind.config.ts         # Tailwind setup
└── package.json               # Scripts and dependencies
```

---

## Internal Logic

### IndexedDB State Management

EasyDATI uses a transactional, mutex-protected model for interacting with local storage. Files are saved with their `uniqueName`, `blob`, and `mimeType`, ensuring reproducible datapacks across reloads. IndexedDB is accessed via `idb`, and concurrent file removals are handled with `async-mutex`.

### File Bucket System

Each table row may be associated with primary or secondary files. A virtual file bucket handles:

* Adding and generating unique filenames
* Retrieving files by name
* Deleting orphaned files when metadata changes

### Tabulator Custom Editors

Custom editors are built for different column types:

* `inputEditor`: Generic text input with auto-validation
* `listEditor`: Dropdown based on precomputed values
* `dateEditor`: Calendar selector formatted as DD/MM/YYYY
* `fileNameEditor`: Handles file replacement and preview
* `secondaryContentEditor`: Dropdown with file list, add/view/delete support

All editors are compatible with Tabulator's render cycle and include blur, key, and focus handlers.

### Import Format Support

ZIP archives can contain:

* One metadata file (CSV or Excel)
* A folder with files linked to the table

For supplier ZIPs, headers are mapped and normalized to match internal schema.
For DATI ZIPs, document and link rows are merged automatically.

### Export Pipeline

Datapacks are exported as normalized CSV with validated data and attached files in a single ZIP package. Special handling ensures:

* Consistent header ordering
* Field trimming and deduplication
* Filename uniqueness
* Clean-up of removed files

---

## Data Flow

1. **Startup**

    * Load last session from IndexedDB
    * Rehydrate table and files

2. **Interaction**

    * Modify cells, add/remove files
    * Validate and normalize on the fly

3. **Autosave**

    * Triggered on change after debounce
    * Saves table data + files to IndexedDB

4. **Export**

    * Generates normalized CSV
    * Assembles into ZIP with attached files

5. **Import**

    * Parses uploaded ZIP
    * Maps and merges documents and links
    * Populates table and file bucket

---

## Deployment

EasyDATI can be deployed as a static SPA. It requires no server-side component.

To build the app:

```bash
npm run build
```

The final output is in the `dist/` folder.

---

## Version History

* **v1.0.0** – March 2024 – Initial release
* **v2.0.2** – May 2024 – Added export logic, refactor storage
* **v3.0.1** – June 2024 – Bug fixes, enhanced validation
* **v4.0.5** – January 2025 – UI overhaul, file viewer integration
* **v5.0.3** – August 2025 – Final stable release, performance tuning

---

## License

This project is licensed under the MIT License.

---

## Author

Developed and maintained by **Jean GUIRAUD (jean.guiraud@thalesaleniaspace.com)**.

For any inquiries or internal deployment documentation, please contact the **Configuration and Data Management** service, specifically the **Process Methods and Tools branch**. The head of PMT is **Bruno BENOIST**, who can be reached at **bruno.benoist@thalesaleniaspace.com**.
