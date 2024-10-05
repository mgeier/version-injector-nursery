import importlib.metadata
from pathlib import Path

import tomlkit

__version__ = '0.0.0'

# TODO: possible actions:
#       - new build has been created
#         - if already in TOML: inject versions only into the new build
#         - if not yet in TOML: add version/variant, inject versions everywhere
#       - manual trigger, inject versions everywhere

# TODO: before each injection batch:
#       - delete subdirectories that are not listed in TOML
#       - delete temporary versions after given delay (based on git information?)
#         "expire_in": "6 months and 4 days", "never"
#         or after a given number is reached?

# TODO: when parsing TOML:
#       - check that all names are unique

def read_toml():
    f = Path('version-injector.toml')
    # If file doesn't exist in current directory -> exception
    config = tomlkit.load(f.open())
    print(config['vanguard'])
    print(config['versions'])
    print(config['variants'])

# TODO: get directory from command line arg or iterate all directories
# TODO: check config file for available versions etc.
def inject():
    for f in Path('pages/0.1.0').rglob('*.html'):
        remainder = f.read_text()
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
            category, sep, remainder = remainder.partition('-below-->')
            if sep == '':
                # TODO: somehow continue?
                raise RuntimeError(
                    'error! malformed marker? missing opening marker?')
            chunks.append(category)
            chunks.append(sep)
            discard, sep, remainder = remainder.partition(
                f'<!--version-injector-injects-{category}-above-->')
            if sep == '':
                raise RuntimeError(
                    f'error/warning? no closing marker for {category!r}')
            chunks.append('\n')
            if category == 'VERSIONS':
                chunks.append('<li>generated content!</li>\n')
                chunks.append('<li>more generated content!</li>\n')
            elif category == 'WARNING':
                chunks.append('<p><b>warning!</b></p>\n')
                chunks.append('<p><b>another warning!</b></p>\n')
            else:
                raise RuntimeError(f'Unknown category: {category!r}')
            chunks.append(sep)
        f.write_text(''.join(chunks))


if __name__ == '__main__':
    read_toml()
    inject()
