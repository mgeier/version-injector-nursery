from pathlib import Path

import jinja2
import tomlkit

CATEGORIES = 'vanguard', 'versions', 'variants', 'unlisted'

# TODO: possible actions:
#       - new build has been created, dirname and category has to be given
#         - if already in TOML: inject versions only into the new build
#           (the given category is ignored)
#         - if not yet in TOML: add version/variant, inject versions everywhere
#       - manual trigger, inject versions everywhere

# TODO: before each injection batch:
#       - delete subdirectories that are not listed in TOML

# TODO: when parsing TOML:
#       - check that all names are unique
#       - if no versions are available: error
#       - check if all the names are non-empty (truthy?)
#       - check if all names to be listed do exist

config_file = Path('version-injector.toml')
# TODO: better exception message?
# If file doesn't exist in current directory -> exception
config = tomlkit.load(config_file.open())
base_path = Path(config['base-path'])
if not base_path.exists():
    raise RuntimeError(f'"base-path" not found: {base_path}')

_loaders = []
_templates_path = config.get('templates-path')
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

version_names = {}
for k in CATEGORIES:
    version_names[k] = config.get(k, [])
warning_templates = {}
for k in CATEGORIES:
    _filename = config.get(k + '-warning')
    if _filename:
        warning_templates[k] = environment.get_template(
            _filename, globals=version_names)

default = config.get('default', (config.get('versions') or [None])[0])
if default:
    default_path = base_path / default
    if not default_path.exists():
        raise RuntimeError(f'default directory not found: {default_path}')
    (base_path / 'index.html').write_text(
        environment.get_template('index.html').render(default=default))
else:
    (base_path / 'index.html').unlink(missing_ok=True)
    pass


def render_warning(template, html_file):
    new_path = base_path / default / html_file
    while not new_path.exists():
        new_path = new_path.parent
    return template.render(replacement={
        'name': default,
        'url': '/' + new_path.relative_to(base_path).as_posix(),
    })


def inject(current):
    for k in CATEGORIES:
        if current in version_names[k]:
            warning_template = warning_templates[k]
            break
    else:
        assert False

    current_path = base_path / current
    for html_file in current_path.rglob('*.html'):
        remainder = html_file.read_text()
        chunks = []
        while remainder:
            prefix, sep, remainder = remainder.partition(
                '<!--version-injector-injects-')
            chunks.append(prefix)
            if sep == '':
                # no more markers found
                assert remainder == ''
                break
            chunks.append(sep)
            section, sep, remainder = remainder.partition('-below-->')
            if sep == '':
                # TODO: somehow continue?
                raise RuntimeError(
                    'error! malformed marker? missing opening marker?')
            chunks.append(section)
            chunks.append(sep)
            discard, sep, remainder = remainder.partition(
                f'<!--version-injector-injects-{section}-above-->')
            if sep == '':
                raise RuntimeError(
                    f'error/warning? no closing marker for {section!r}')
            chunks.append('\n')
            if section == 'VERSIONS':
                chunks.append('<li>generated content!</li>\n')
                chunks.append('<li>more generated content!</li>\n')
            elif section == 'WARNING':
                if default and current != default and warning_template:
                    warning = render_warning(
                        warning_template, html_file.relative_to(current_path))
                    chunks.append(warning)
            else:
                raise RuntimeError(f'Unknown section: {section!r}')
            chunks.append(sep)
        html_file.write_text(''.join(chunks))


# TODO: check command, potentially iterate over directories
# TODO: if necessary, add given version to the appropriate list

inject('0.1.0')
# TODO: if necessary, save TOML file (after everything was successful)
