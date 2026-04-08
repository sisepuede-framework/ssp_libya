const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, VerticalAlign,
  PageOrientation, HeadingLevel
} = require('docx');
const fs = require('fs');

const rows = JSON.parse(fs.readFileSync('../transformations_description/annex_data.json', 'utf8'));

const BAU_LABEL    = rows[0]?.bau_label           ?? "BAU";
const UNCOND_LABEL = rows[0]?.unconditional_label  ?? "Unconditional";
const COND_LABEL   = rows[0]?.conditional_label    ?? "Conditional";

// A4 landscape content width ≈ 297 − 30 = 267 mm ≈ 15120 DXA (1.5 cm margins)
const TABLE_WIDTH    = 15120;
const COL_TRANSFORM  = 2520;
const COL_POLICY     = 5400;
const COL_BAU        = 2400;
const COL_UNCOND     = 2400;
const COL_COND       = 2400;

const FONT_SIZE = 17;

const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };

const PAD = { top: 40, bottom: 40, left: 80, right: 80 };

function run(text, opts = {}) {
  return new TextRun({ text, font: "Times New Roman", size: FONT_SIZE, color: "000000", ...opts });
}
function para(children, align = AlignmentType.LEFT) {
  return new Paragraph({ alignment: align, spacing: { before: 20, after: 20 }, children });
}

function headerCell(text, width) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders,
    margins: PAD,
    verticalAlign: VerticalAlign.CENTER,
    children: [para([run(text, { bold: true, size: FONT_SIZE })], AlignmentType.CENTER)],
  });
}

const headerRow = new TableRow({
  tableHeader: true,
  children: [
    headerCell("Transformation",     COL_TRANSFORM),
    headerCell("Policy Description", COL_POLICY),
    headerCell(BAU_LABEL,            COL_BAU),
    headerCell(UNCOND_LABEL,         COL_UNCOND),
    headerCell(COND_LABEL,           COL_COND),
  ],
});

function sectorHeaderRow(label) {
  return new TableRow({
    children: [new TableCell({
      columnSpan: 5,
      width:   { size: TABLE_WIDTH, type: WidthType.DXA },
      borders,
      margins: PAD,
      verticalAlign: VerticalAlign.CENTER,
      children: [para([run(label, { bold: true, size: FONT_SIZE })], AlignmentType.LEFT)],
    })],
  });
}

function dataCell(text, width) {
  return new TableCell({
    width:   { size: width, type: WidthType.DXA },
    borders,
    margins: PAD,
    verticalAlign: VerticalAlign.TOP,
    children: [para([run(text, { size: FONT_SIZE })])],
  });
}

function groupBySector(rows) {
  const groups = [];
  let current = null;
  for (const row of rows) {
    if (!current || current.label !== row.subsector_label) {
      current = { label: row.subsector_label, rows: [] };
      groups.push(current);
    }
    current.rows.push(row);
  }
  return groups;
}

const tableRows = [headerRow];
const groups = groupBySector(rows);

groups.forEach((group) => {
  tableRows.push(sectorHeaderRow(group.label));

  group.rows.forEach((row) => {
    tableRows.push(new TableRow({
      children: [
        dataCell(row.transformation_name, COL_TRANSFORM),
        dataCell(row.policy_description,  COL_POLICY),
        dataCell(row.bau,                 COL_BAU),
        dataCell(row.unconditional,       COL_UNCOND),
        dataCell(row.conditional,         COL_COND),
      ],
    }));
  });
});

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Times New Roman", size: FONT_SIZE, color: "000000" } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: {
          width:       15840,
          height:      12240,
          orientation: PageOrientation.LANDSCAPE,
        },
        margin: { top: 851, right: 851, bottom: 851, left: 851 },
      },
    },
    children: [
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun({
          text: "Annex: Transformation Parameters by Pathway",
          font: "Times New Roman", size: 28, bold: true, color: "000000",
        })],
      }),
      new Paragraph({
        children: [new TextRun({
          // text: "The table below presents all SISEPUEDE transformations included in the modelling framework, " +
          //       "with the magnitude parameter applied in each scenario pathway. " +
          //       "Cells marked \u2018No policy\u2019 indicate the transformation is not activated in that pathway. " +
          //       "BAU = Business-as-usual (strategy_NDC); Unconditional = LEP pathway; Conditional = Conditional pathway.",
          // font: "Calibri", size: 18, color: "000000",
        })],
        spacing: { after: 200 },
      }),
      new Table({
        width:        { size: TABLE_WIDTH, type: WidthType.DXA },
        columnWidths: [COL_TRANSFORM, COL_POLICY, COL_BAU, COL_UNCOND, COL_COND],
        rows:         tableRows,
      }),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('../transformations_description/annex_transformations.docx', buf);
  console.log('Done → annex_transformations.docx');
});
