def extract_npm_dependencies_dict(names: list[str]):
    dependencies = {
        "@types/jest": "^29.5.6",
        "@types/node": "^20.11.10",  # peer dependency for @youwol/tsconfig
        "@types/webpack": "^5.28.0",
        "@youwol/cdn-client": "^2.1.0",
        "@youwol/eslint-config": "^1.2.0",
        "@youwol/flux-view": "^1.2.0",
        "@youwol/http-clients": "^3.0.0",
        "@youwol/jest-preset": "^1.2.0",
        "@youwol/prettier-config": "^1.2.0",
        "@youwol/rx-vdom": "^1.0.1",
        "@youwol/tsconfig": "^1.2.0",
        "@youwol/webpm-client": "^3.0.0",
        "css-loader": "^6.8.1",
        "del-cli": "^5.1.0",
        "file-loader": "6.2.0",
        "html-webpack-plugin": "5.5.3",
        "isomorphic-fetch": "^3.0.0",
        "mini-css-extract-plugin": "^2.7.6",
        "rxjs": "^7.5.6",
        "source-map-loader": "4.0.1",
        "ts-loader": "9.5.0",
        "ts-node": "10.9.2",  # peer dependency for @youwol/tsconfig
        "tsx": "4.7.0",
        "typedoc": "^0.25.7",
        "typescript": "5.3.3",  # peer dependency for @youwol/tsconfig
        "webpack": "^5.89.0",
        "webpack-bundle-analyzer": "^4.9.1",
        "webpack-cli": "5.1.4",
        "webpack-dev-server": "^4.15.1",
    }
    return {k: v for k, v in dependencies.items() if k in names}
