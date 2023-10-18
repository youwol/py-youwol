# typing
from typing import List


def extract_npm_dependencies_dict(names: List[str]):
    dependencies = {
        "@types/node": "^20.8.7",
        "del-cli": "^5.1.0",
        "typescript": "^5.2.2",
        "ts-loader": "^9.5.0",
        "ts-node": "^10.9.1",
        "webpack": "^5.89.0",
        "webpack-bundle-analyzer": "^4.9.1",
        "webpack-cli": "5.1.4",
        "@youwol/cdn-client": "^2.1.0",
        "@youwol/http-clients": "^2.0.5",
        "@youwol/prettier-config": "^0.1.0",
        "@youwol/eslint-config": "^0.1.0",
        "@youwol/tsconfig": "^0.1.0",
        "@types/jest": "^29.5.6",
        "@youwol/jest-preset": "^0.1.0",
        "isomorphic-fetch": "^3.0.0",
        "@youwol/flux-view": "^1.1.1",
        "rxjs": "^6.5.5",
        "css-loader": "^6.8.1",
        "file-loader": "6.2.0",
        "html-webpack-plugin": "5.5.3",
        "mini-css-extract-plugin": "^2.7.6",
        "source-map-loader": "4.0.1",
        "webpack-dev-server": "^4.15.1",
        "ts-lib": "^0.0.5",
        "typedoc": "^0.25.2",
        "@types/webpack": "^5.28.0",
    }
    return {k: v for k, v in dependencies.items() if k in names}
