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

version_names = { c: config.get(c, []) for c in CATEGORIES }
all_listed_versions = [
    v for c in CATEGORIES if c != 'unlisted' for v in version_names[c]]

warning_templates = {
    c: environment.get_template(filename, globals=version_names)
    for c in CATEGORIES if (filename := config.get(c + '-warning'))
}

default = config.get('default', (config.get('versions') or [None])[0])
if default:
    default_path = base_path / default
    if not default_path.exists():
        raise RuntimeError(f'default directory not found: {default_path}')
    if default not in all_listed_versions:
        raise RuntimeError(f'unlisted default version: {default!r}')
    (base_path / 'index.html').write_text(
        environment.get_template('index.html').render(default=default))
else:
    (base_path / 'index.html').unlink(missing_ok=True)


version_list_template = environment.get_template(
    'version-list.html', globals=version_names)


def render_version_list(vars):
    return version_list_template.render(vars)


def render_warning(template, url):
    return template.render(replacement={
        'name': default,
        'url': url,
    })


# this will be re-used by all inject() calls
cache = {}


def inject(current):
    for c in CATEGORIES:
        if current in version_names[c]:
            warning_template = warning_templates[c]
            break
    else:
        assert False

    current_path = base_path / current
    for html_path in current_path.rglob('*.html'):
        relative_html_path = html_path.relative_to(current_path)
        relative_html_url = relative_html_path.as_posix()
        links = cache.setdefault(relative_html_url, {})
        for v in all_listed_versions:
            if v not in links:
                if v == current:
                    # we know that this file exists
                    links[v] = f'/{v}/{relative_html_url}'
                    continue
                new_path = base_path / v / relative_html_path
                while not new_path.exists():
                    new_path = new_path.parent
                links[v] = '/' + new_path.relative_to(base_path).as_posix()

        remainder = html_path.read_text()
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
                chunks.append(render_version_list({
                    'links': links,
                    'current': current,
                }))
            elif section == 'WARNING':
                if (default and current != default and warning_template
                        # the first entry in "versions" gets no warning
                        and current != (config.get('versions') or [''])[0]):
                    warning = render_warning(warning_template, links[default])
                    chunks.append(warning)
            else:
                raise RuntimeError(f'Unknown section: {section!r}')
            chunks.append(sep)
        html_path.write_text(''.join(chunks))


# TODO: check command, potentially iterate over directories
# TODO: if necessary, add given version to the appropriate list

inject('0.1.0')
# TODO: if necessary, save TOML file (after everything was successful)
