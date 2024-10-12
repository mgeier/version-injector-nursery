"""Inject version information into HTML files."""
import argparse
from pathlib import Path

import jinja2
from tomlkit.toml_file import TOMLFile

from version_injector import inject_files

CATEGORIES = 'vanguard', 'versions', 'variants', 'unlisted'

parser = argparse.ArgumentParser(
    prog='python -m version_injector',
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument(
    'version', nargs='?', metavar='VERSION',
    type=str,
    help='name of version that has been added/updated')
parser.add_argument(
    'category', nargs='?', choices=CATEGORIES,
    help="if version doesn't exist yet, it will be added to this category")
args = parser.parse_args()

# TODO: no argument: inject all versions

config_file = TOMLFile('version-injector.toml')
# TODO: better exception message?
# If file doesn't exist in current directory -> exception
config = config_file.read()
base_path = Path(config['base-path'])
if not base_path.exists():
    raise RuntimeError(f'"base-path" not found: {base_path}')
base_url = config.get('base-url', '')

# TODO: when parsing TOML:
#       - if no versions are available: error
#       - check if all the names are non-empty (truthy?)
#       - check if all names to be listed do exist

all_versions = [v for c in CATEGORIES for v in config.get(c, [])]
if len(all_versions) != len(set(all_versions)):
    # TODO: show which are duplicates
    parser.exit(f'duplicate version names')
if args.version:
    if not args.category:
        parser.error('either 0 or 2 arguments are required')
    if args.version not in all_versions:
        names = config.setdefault(args.category, [])
        if not (base_path / args.version).is_dir():
            parser.exit(f'directory not found: {args.version!r}')
        names.insert(0, args.version)
        config_file.write(config)
        # re-compute because a version has been added:
        all_versions = [v for c in CATEGORIES for v in config.get(c, [])]
else:
    # TODO: delete subdirectories that are not in all_versions
    pass

_loaders = []
_templates_path = config.get('templates-path')
# TODO: make sure it's relative to the TOML location
if _templates_path:
    if not Path(_templates_path).exists():
        raise RuntimeError(f'"templates-path" not found: {_templates_path!r}')
    _loaders.append(
        jinja2.FileSystemLoader(_templates_path, followlinks=True))
_loaders.append(jinja2.PackageLoader('version_injector', '_templates'))
environment = jinja2.Environment(
    loader=jinja2.ChoiceLoader(_loaders),
    keep_trailing_newline=True,
)

version_names = { c: config.get(c, []) for c in CATEGORIES }
all_listed_versions = [
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
    default_path = base_path / default
    if not default_path.exists():
        raise RuntimeError(f'default directory not found: {default_path}')
    if default not in all_listed_versions:
        raise RuntimeError(f'unlisted default version: {default!r}')
    (base_path / 'index.html').write_text(
        environment.get_template('index.html').render(
            default=default, base_url=base_url))
else:
    # TODO: create index page with all_listed_versions (if empty: ?)
    (base_path / 'index.html').unlink(missing_ok=True)

(base_path / '404.html').write_text(
    environment.get_template('404.html', globals=version_names).render(
        default=default, base_url=base_url))

version_list_template = environment.get_template(
    'version-list.html', globals=version_names)


# this will be re-used by all inject() calls
cache = {}


def prepare_injection(current, relative_html_path):
    relative_html_url = relative_html_path.as_posix()
    links = cache.setdefault(relative_html_url, {})
    for c in CATEGORIES:
        if current in version_names[c]:
            warning_template = warning_templates.get(c)
            break
    else:
        assert False
    for v in all_listed_versions:
        if v not in links:
            if v == current:
                # we know that this file exists
                links[v] = f'{base_url}/{v}/{relative_html_url}'
                continue
            new_path = base_path / v / relative_html_path
            while not new_path.exists():
                new_path = new_path.parent
            links[v] = '/'.join([
                base_url, new_path.relative_to(base_path).as_posix()])

    def injection(section):
        if section == 'VERSIONS':
            return version_list_template.render({
                'links': links,
                'current': current,
            })
        elif section == 'WARNING':
            if (default and current != default and warning_template
                    # the first entry in "versions" gets no warning
                    and current != (config.get('versions') or [''])[0]):
                return warning_template.render(replacement={
                    'name': default,
                    'url': links[default],
                })
        return ''

    return injection


def inject(current):
    try:
        inject_files(base_path, current, prepare_injection)
    except RuntimeError as e:
        parser.exit(str(e))


for v in all_versions:
    inject(v)
