import { youwolInfo } from '../auto-generated-toml'

export function formatPythonVersions() {
    return youwolInfo.pythons.reduce(
        (acc, e) => (acc == '' ? `**${e}**` : `${acc}, **${e}**`),
        '',
    )
}
