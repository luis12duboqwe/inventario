
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

function getAllFiles(dirPath: string, arrayOfFiles: string[] = []) {
  const files = fs.readdirSync(dirPath);

  files.forEach(function(file) {
    if (fs.statSync(dirPath + "/" + file).isDirectory()) {
      getAllFiles(dirPath + "/" + file, arrayOfFiles);
    } else {
      if (file.endsWith('.ts') || file.endsWith('.tsx')) {
          if (!file.endsWith('.d.ts')) {
            arrayOfFiles.push(path.join(dirPath, "/", file));
          }
      }
    }
  });

  return arrayOfFiles;
}

describe('Code Quality', () => {
  it('should not contain "as any" or ": any" in frontend source files', () => {
    const srcDir = path.resolve(__dirname, '../../src');
    const files = getAllFiles(srcDir);

    const errors: string[] = [];

    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      const lines = content.split('\n');

      lines.forEach((line, index) => {
        if (line.includes('as any') || line.includes(': any')) {
           // Ignore comments
           if (!line.trim().startsWith('//') && !line.trim().startsWith('*') && !line.trim().startsWith('/*')) {
             // Ignore the test file itself
             if (!file.includes('code-quality.test.ts')) {
                 errors.push(`${path.relative(srcDir, file)}:${index + 1}: ${line.trim()}`);
             }
           }
        }
      });
    }

    expect(errors).toEqual([]);
  });
});
