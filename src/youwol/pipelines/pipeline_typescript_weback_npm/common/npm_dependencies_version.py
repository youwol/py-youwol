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
        "webpack-cli": "4.9.2",
        "@youwol/cdn-client": "^2.1.0",
        "@youwol/http-clients": "^2.0.5",
        "@youwol/prettier-config": "^0.1.0",
        "@youwol/eslint-config": "^0.1.0",
        "@youwol/tsconfig": "^0.1.0",
        "@types/jest": "^29.2.4",
        "@youwol/jest-preset": "0.1.0",
        "isomorphic-fetch": "^3.0.0",
    }
    return {k: v for k, v in dependencies.items() if k in names}
