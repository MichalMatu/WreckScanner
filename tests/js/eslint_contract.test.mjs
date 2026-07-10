import assert from 'node:assert/strict';
import { test } from 'node:test';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ESLint } from 'eslint';

const rootDir = dirname(dirname(dirname(fileURLToPath(import.meta.url))));

test('frontend lint rejects unknown globals and unused local variables', async () => {
    const eslint = new ESLint({ cwd: rootDir });
    const [result] = await eslint.lintText(
        'function lintProbe() { const unusedLocal = 1; return definitelyMissingFrontendGlobal; }',
        { filePath: join(rootDir, 'web', 'app', 'api.js') },
    );
    const ruleIds = new Set(result.messages.map(message => message.ruleId));

    assert.ok(ruleIds.has('no-undef'));
    assert.ok(ruleIds.has('no-unused-vars'));
});
