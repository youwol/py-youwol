from typing import List


def extract_npm_dependencies_dict(names: List[str]):
    dependencies = {
        "@types/node": "^20.8.6",
        "del-cli": "^5.0.0",
        "typescript": "^4.7.4",
        "ts-loader": "^9.3.1",
        "ts-node": "^10.9.1",
        "webpack": "5.73.0",
        "webpack-bundle-analyzer": "^4.5.0",
        "webpack-cli": "4.10.0",
        "@youwol/cdn-client": "^2.1.0",
        "@youwol/http-clients": "^2.0.5",
        "@youwol/prettier-config": "^0.1.0",
        "@youwol/eslint-config": "^0.1.0",
        "@youwol/tsconfig": "^0.1.0",
        "@types/jest": "^29.2.4",
        "@youwol/jest-preset": "0.1.0",
        "isomorphic-fetch": "^3.0.0",
        "@youwol/flux-view": "^1.1.1",
        "rxjs": "^6.5.5",
        "css-loader": "^6.7.2",
        "file-loader": "6.2.0",
        "html-webpack-plugin": "5.2.0",
        "mini-css-extract-plugin": "^2.7.0",
        "source-map-loader": "2.0.1",
        "webpack-dev-server": "^4.7.1",
        "ts-lib": "^0.0.5",
        "typedoc": "^0.23.8",
        "@types/webpack": "^5.28.0"
    }
    return {k: v for k, v in dependencies.items() if k in names}
