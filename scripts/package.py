"""Package Lucretia's color themes using the VSIX ZIP/XML format."""
from io import BytesIO
from zipfile import ZIP_STORED, ZipFile, ZipInfo
from xml.etree import ElementTree as ET

VSIX_NS = 'http://schemas.microsoft.com/developer/vsx-schema/2011'
TYPES_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'


def zip_bytes(files):
    """Use fixed timestamps and permissions so repeated builds are identical."""
    out = BytesIO()
    with ZipFile(out, 'w') as archive:
        for name, content in sorted(files.items()):
            entry = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = ZIP_STORED
            archive.writestr(entry, content)
    return out.getvalue()


def xml_bytes(element):
    ET.indent(element, space='  ')
    return ET.tostring(element, encoding='utf-8', xml_declaration=True) + b'\n'


def vscode_package(version):
    return {
        'name': 'lucretia-theme', 'displayName': 'Lucretia',
        'description': 'Light, Dark, and Paper color themes for code and notes.',
        'version': version, 'publisher': 'sugu', 'engines': {'vscode': '^1.75.0'},
        'categories': ['Themes'],
        'repository': {'type': 'git', 'url': 'https://github.com/sk-226/lucretia.git'},
        'contributes': {'themes': [
            {'label': f'Lucretia {kind.capitalize()}', 'uiTheme': 'vs-dark' if kind == 'dark' else 'vs',
             'path': f'./themes/lucretia-{kind}-color-theme.json'}
            for kind in ('light', 'dark', 'paper')]},
    }


def vsix_bytes(pkg, files):
    root = ET.Element('PackageManifest', {'Version': '2.0.0', 'xmlns': VSIX_NS})
    metadata = ET.SubElement(root, 'Metadata')
    ET.SubElement(metadata, 'Identity', {'Language': 'en-US', 'Id': pkg['name'],
                  'Version': pkg['version'], 'Publisher': pkg['publisher']})
    ET.SubElement(metadata, 'DisplayName').text = pkg['displayName']
    ET.SubElement(metadata, 'Description', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'}).text = pkg['description']
    ET.SubElement(metadata, 'Tags').text = 'theme,color-theme,__web_extension'
    ET.SubElement(metadata, 'Categories').text = 'Themes'
    ET.SubElement(metadata, 'GalleryFlags').text = 'Public'
    properties = ET.SubElement(metadata, 'Properties')
    for name, value in {
        'Microsoft.VisualStudio.Code.Engine': pkg['engines']['vscode'],
        'Microsoft.VisualStudio.Code.ExtensionKind': 'ui,workspace,web',
        'Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown': 'true',
    }.items():
        ET.SubElement(properties, 'Property', {'Id': name, 'Value': value})
    installation = ET.SubElement(root, 'Installation')
    ET.SubElement(installation, 'InstallationTarget', {'Id': 'Microsoft.VisualStudio.Code'})
    ET.SubElement(root, 'Dependencies')
    assets = ET.SubElement(root, 'Assets')
    for kind, path in (('Microsoft.VisualStudio.Code.Manifest', 'package.json'),
                       ('Microsoft.VisualStudio.Services.Content.Details', 'README.md')):
        ET.SubElement(assets, 'Asset', {'Type': kind, 'Path': f'extension/{path}', 'Addressable': 'true'})
    types = ET.Element('Types', {'xmlns': TYPES_NS})
    for extension, content_type in (('.json', 'application/json'), ('.md', 'text/markdown'),
                                    ('.vsixmanifest', 'text/xml')):
        ET.SubElement(types, 'Default', {'Extension': extension, 'ContentType': content_type})
    return zip_bytes({'extension.vsixmanifest': xml_bytes(root), '[Content_Types].xml': xml_bytes(types),
                      **{f'extension/{name}': value for name, value in files.items()}})
