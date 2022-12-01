/** @format */

module.exports = {
    preset: 'ts-jest',
    testRunner: 'jest-jasmine2',
    testEnvironment: 'jsdom',
    testEnvironmentOptions: {
        url: 'http://localhost:2001',
    },
    reporters: ['default', 'jest-junit'],
    modulePathIgnorePatterns: ['/dist', '/.template'],
}
