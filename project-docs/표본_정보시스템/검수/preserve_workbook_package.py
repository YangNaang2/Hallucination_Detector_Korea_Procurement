"""Preserve the submitted XLSX package around Artifact Tool's edited cell values.

The exporter omits the source autoFilter and normalizes styles. Copy only the
already-authored changed values back into the original package, preserving all
other parts, style references, dimensions, filters and views byte-for-byte.
"""
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

source, output = map(Path, sys.argv[1:3])
ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
ET.register_namespace('', ns['s'])
changes = json.loads((Path(os.environ['TEMP']) / 'team3-changes.json').read_text(encoding='utf-8'))
cells = {change['cell'] for change in changes}
with zipfile.ZipFile(output) as authored:
    strings = []
    if 'xl/sharedStrings.xml' in authored.namelist():
        strings = [''.join(t.text or '' for t in si.findall('.//s:t', ns))
                   for si in ET.fromstring(authored.read('xl/sharedStrings.xml')).findall('s:si', ns)]
    values = {}
    for c in ET.fromstring(authored.read('xl/worksheets/sheet1.xml')).findall('.//s:c', ns):
        if c.attrib['r'] not in cells:
            continue
        if c.get('t') == 's':
            value = strings[int(c.find('s:v', ns).text)]
        elif c.get('t') == 'inlineStr':
            value = ''.join(t.text or '' for t in c.findall('.//s:t', ns))
        else:
            value = c.find('s:v', ns).text
        values[c.attrib['r']] = value
assert set(values) == cells
tmp = output.with_suffix('.preserved.xlsx')
with zipfile.ZipFile(source) as original, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as final:
    for part in original.infolist():
        data = original.read(part.filename)
        if part.filename == 'xl/worksheets/sheet1.xml':
            sheet = ET.fromstring(data)
            for c in sheet.findall('.//s:c', ns):
                if c.get('r') in values:
                    for child in list(c):
                        c.remove(child)
                    c.set('t', 'inlineStr')
                    inline = ET.SubElement(c, '{'+ns['s']+'}is')
                    text = ET.SubElement(inline, '{'+ns['s']+'}t')
                    text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                    text.text = values[c.get('r')]
            data = ET.tostring(sheet, encoding='utf-8', xml_declaration=True)
        final.writestr(part, data)
os.replace(tmp, output)
print('Preserved original package with', len(cells), 'authored text edits')
