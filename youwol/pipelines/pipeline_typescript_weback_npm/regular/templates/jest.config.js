module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'jsdom',
    testURL: 'http://localhost:2001',
    reporters: ['default', 'jest-junit'],
    modulePathIgnorePatterns: ['/dist'],
}
