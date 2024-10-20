"""Inject version information into HTML files."""
import argparse
from pathlib import Path

import jinja2
from tomlkit.toml_file import TOMLFile

CATEGORIES = 'vanguard', 'versions', 'variants', 'unlisted'

parser = argparse.ArgumentParser(
    prog='python -m version_injector',
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument(
    'version', metavar='VERSION', type=str,
    help='name of version that has been added/updated')
parser.add_argument(
    'category', choices=CATEGORIES,
    help="if VERSION doesn't exist yet, it will be added to this category")
parser.add_argument(
    '--inject-only-one', action='store_true',
    help='only inject into the given version (default: all versions)')
parser.add_argument(
    '--docs-path', required=True, type=Path,
    help='where the different versions of the documentation are stored')
parser.add_argument(
    '--pathname-prefix', default='', type=str,
    help="beginning of the 'pathname' component of the final URL")
args = parser.parse_args()

config_file = TOMLFile('version-injector.toml')
# TODO: better exception message?
# If file doesn't exist in current directory -> exception
config = config_file.read()
if not args.docs_path.exists():
    parser.error(f"'--docs-path' not found: {args.docs_path}")
if args.pathname_prefix and not args.pathname_prefix.startswith('/'):
    parser.error("'--pathname-prefix' must be empty string or start with '/'")

# TODO: when parsing TOML:
#       - if no versions are available: error
#       - check if all the names are non-empty (truthy?)
#       - check if all names to be listed do exist

all_versions = [v for c in CATEGORIES for v in config.get(c, [])]
if len(all_versions) != len(set(all_versions)):
    # TODO: show which are duplicates
    parser.exit(f'duplicate version names')
if args.version not in all_versions:
    names = config.setdefault(args.category, [])
    if not (args.docs_path / args.version).is_dir():
        parser.exit(f'directory not found: {args.version!r}')
    names.insert(0, args.version)
    config_file.write(config)
    # re-compute because a version has been added:
    all_versions = [v for c in CATEGORIES for v in config.get(c, [])]

# TODO: delete subdirectories that are not in all_versions

_loaders = []
_templates_path = config.get('templates-path')
# TODO: make sure it's relative to the TOML location
if _templates_path:
    if not Path(_templates_path).exists():
        parser.exit(f'"templates-path" not found: {_templates_path!r}')
    _loaders.append(
        jinja2.FileSystemLoader(_templates_path, followlinks=True))
_loaders.append(jinja2.PackageLoader('version_injector', '_templates'))
environment = jinja2.Environment(
    loader=jinja2.ChoiceLoader(_loaders),
    keep_trailing_newline=True,
)

version_names = { c: config.get(c, []) for c in CATEGORIES }
listed_versions = [
    v for c in CATEGORIES if c != 'unlisted' for v in version_names[c]]

warning_templates = {
    c: environment.get_template(filename, globals=version_names)
    for c in CATEGORIES if (filename := config.get(c + '-warning'))
}

default = config.get('default', (
    config.get('versions') or
    config.get('vanguard') or
    config.get('variants') or [None])[0])
if default:
    default_path = args.docs_path / default
    if not default_path.exists():
        parser.exit(f'default directory not found: {default_path}')
    if default not in listed_versions:
        parser.exit(f'unlisted default version: {default!r}')
    (args.docs_path / 'index.html').write_text(
        environment.get_template('index.html').render(
            default=default, pathname_prefix=args.pathname_prefix))
else:
    # TODO: create index page with listed_versions (if empty: ?)
    (args.docs_path / 'index.html').unlink(missing_ok=True)

(args.docs_path / '404.html').write_text(
    environment.get_template('404.html', globals=version_names).render(
        default=default, pathname_prefix=args.pathname_prefix))

version_list_template = environment.get_template(
    'version-list.html', globals=version_names)


cache = {}


def create_context(current, relative_path):
    # Find links from the current version of the current HTML file
    # to the same file (or some parent directory) in all listed versions.
    links = cache.setdefault(relative_path, {})
    for v in listed_versions:
        if v not in links:
            new_path = args.docs_path / v / relative_path
            while not new_path.exists():
                new_path = new_path.parent
            links[v] = '/'.join([
                args.pathname_prefix,
                new_path.relative_to(args.docs_path).as_posix()])
    return {
        'current': current,
        'default': default,
        'links': links,
    }


def inject_file(path, injection):
    remainder = path.read_text()
    chunks = []
    while remainder:
        left = '<!--inject-'
        prefix, left, remainder = remainder.partition(left)
        chunks.append(prefix)
        if left == '':
            # no more markers found
            assert remainder == ''
            break
        chunks.append(left)
        right = '-below-->'
        section, right, remainder = remainder.partition(right)
        # If the marker is malformed, "section" might span multiple lines
        if right == '' or '\n' in section:
            marker = left + section.split('\n')[0]
            parser.exit(f'malformed opening marker: {marker!r}')
        chunks.append(section)
        chunks.append(right)
        closer = f'<!--inject-{section}-above-->'
        discard, closer, remainder = remainder.partition(closer)
        if closer == '':
            parser.exit(f'no closing marker for {section!r}')
        chunks.append('\n')  # Any existing newlines were discarded
        chunks.append(injection(section))
        chunks.append(closer)
    path.write_text(''.join(chunks))


def inject_directory(current):
    # TODO: proper logging
    print('injecting into', current)
    for c in CATEGORIES:
        if current in version_names[c]:
            warning_template = warning_templates.get(c)
            break
    else:
        assert False
    current_path = args.docs_path / current
    for path in current_path.rglob('*.html'):
        context = create_context(current, path.relative_to(current_path))

        def injection(section):
            if section == 'VERSIONS':
                return version_list_template.render(context)
            elif section == 'WARNING':
                if (default and current != default and warning_template
                        # the first entry in "versions" gets no warning
                        and current != (config.get('versions') or [''])[0]):
                    return warning_template.render(context)
            return ''

        inject_file(path, injection)


if args.inject_only_one:
    inject_directory(args.version)
else:
    for v in all_versions:
        inject_directory(v)
