import { test, expect } from '@playwright/test'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'

function pdf(text) {
  const stream = `BT /F1 12 Tf 72 720 Td (${text}) Tj ET`
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]
  let content = '%PDF-1.4\n'
  const offsets = [0]
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(content))
    content += `${index + 1} 0 obj\n${object}\nendobj\n`
  })
  const xref = Buffer.byteLength(content)
  content += `xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(offset => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return Buffer.from(content)
}

const api = 'http://127.0.0.1:8029'
const navigate = async (page, name) => {
  await page.getByRole('navigation', { name: 'Workspace' }).getByRole('link', { name, exact: true }).click()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
}

test('real PDF upload, extraction, pagination, comparison, reprocess, and deletion', async ({ page, request }) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  expect(await (await request.get(`${api}/documents`)).json()).toEqual([])
  await page.goto('/')
  await expect(page.getByText('Backend connected', { exact: true })).toBeVisible()
  const claims = Array.from({ length: 25 }, (_, i) => `Revenue metric ${i} increased significantly.`)
  async function upload(name, text) {
    const response = page.waitForResponse(response => response.url() === `${api}/documents` && response.request().method() === 'POST')
    await page.locator('input[type=file]').first().setInputFiles({ name, mimeType: 'application/pdf', buffer: pdf(text) })
    const result = await response
    expect(result.ok()).toBeTruthy()
    const document = await result.json()
    expect(document.status).toBe('processed')
    expect(document.stored_path).toContain('factflow-browser-')
    expect(existsSync(document.stored_path)).toBe(true)
    await expect(page.getByRole('button', { name: `View ${name}`, exact: true })).toBeVisible()
    return document
  }
  const first = await upload('first.pdf', claims.join(' '))
  await page.getByRole('button', { name: 'View first.pdf', exact: true }).click()
  const detail = page.locator('.document-detail')
  await expect(detail.getByText('Showing 1–20 of 25')).toBeVisible()
  await detail.getByRole('button', { name: 'Next' }).click()
  await expect(detail.getByText('Showing 21–25 of 25')).toBeVisible()
  await expect(detail.locator('.fact-row')).toHaveCount(5)
  const sourceLink = detail.getByRole('link', { name: 'Open PDF · page 1 (new tab)' }).first()
  await expect(sourceLink).toHaveAttribute('href', `${api}/documents/${first.id}/source#page=1`)
  await expect(sourceLink).toHaveAttribute('target', '_blank')
  const sourceResponse = await request.get(await sourceLink.getAttribute('href'))
  expect(sourceResponse.ok()).toBe(true)
  expect(sourceResponse.headers()['content-type']).toBe('application/pdf')
  expect(await sourceResponse.body()).toEqual(readFileSync(first.stored_path))

  await expect(detail.locator('.fact-row span').first()).toContainText('Page 1')
  const second = await upload('second.pdf', claims[0])
  await navigate(page, 'Facts')
  await page.getByRole('combobox', { name: 'Source' }).selectOption(first.id)
  await page.getByRole('textbox', { name: 'Search' }).fill('metric 24')
  await expect(page.locator('.fact-browser-card')).toHaveCount(1)
  await expect(page.locator('.fact-browser-card')).toContainText(claims[24])
  await expect(page.locator('.fact-browser-card a')).toHaveAttribute('href', `${api}/documents/${first.id}/source#page=1`)
  await navigate(page, 'Comparisons')
  await page.getByRole('combobox', { name: 'Source' }).selectOption(second.id)
  await page.getByRole('combobox', { name: 'Relationship' }).selectOption('agreement')
  await expect(page.locator('.comparison-card')).toHaveCount(1)
  await expect(page.locator('.comparison-card')).toContainText('Matching wording')
  await expect(page.locator('.comparison-card')).toContainText('first.pdf')
  await expect(page.locator('.comparison-card')).toContainText('second.pdf')
  const sourceLinks = await page.locator('.comparison-card a').evaluateAll(links => links.map(link => link.href))
  expect(sourceLinks.sort()).toEqual([`${api}/documents/${first.id}/source#page=1`, `${api}/documents/${second.id}/source#page=1`].sort())
  await navigate(page, 'Documents')
  await page.getByRole('button', { name: 'View first.pdf', exact: true }).click()
  await expect(detail.getByText('Showing 1–20 of 25')).toBeVisible()
  const originalBytes = readFileSync(first.stored_path)
  writeFileSync(first.stored_path, 'broken PDF')
  const failed = page.waitForResponse(response => response.url().endsWith(`/documents/${first.id}/process`))
  await page.getByRole('button', { name: 'Reprocess first.pdf', exact: true }).click()
  expect((await failed).status()).toBe(422)
  const retainedMessage = 'Latest extraction failed. This evidence is retained from an earlier successful run.'
  await expect(detail.getByText(retainedMessage)).toBeVisible()
  await expect(detail.getByText('extraction_failed', { exact: true })).toBeVisible()
  await navigate(page, 'Facts')
  await expect(page.getByText(retainedMessage)).toBeVisible()
  await expect(page.locator('.stat-card').filter({ hasText: 'Facts' }).locator('.stat-number')).toHaveText('1')
  await navigate(page, 'Comparisons')
  await expect(page.getByText(retainedMessage)).toBeVisible()
  await navigate(page, 'Documents')
  await expect(page.locator('.stat-card').filter({ hasText: 'Facts' }).locator('.stat-number')).toHaveText('—')
  writeFileSync(first.stored_path, originalBytes)
  const before = await (await request.get(`${api}/facts?document_id=${first.id}`)).json()
  const processed = page.waitForResponse(response => response.url().endsWith(`/documents/${first.id}/process`))
  await page.getByRole('button', { name: 'Reprocess first.pdf', exact: true }).click()
  expect((await processed).ok()).toBe(true)
  await expect(detail.getByText('processed', { exact: true })).toBeVisible()
  await expect(detail.getByText(retainedMessage)).toHaveCount(0)
  const after = await (await request.get(`${api}/facts?document_id=${first.id}`)).json()
  expect(after.total).toBe(25)
  expect(after.items.some(item => before.items.some(old => old.id === item.id))).toBe(false)
  for (const document of [first, second]) {
    page.once('dialog', dialog => dialog.accept())
    await page.getByRole('button', { name: `Delete ${document.filename}`, exact: true }).click()
    await expect(page.getByRole('button', { name: `View ${document.filename}`, exact: true })).toHaveCount(0)
    expect(existsSync(document.stored_path)).toBe(false)
  }
  expect(await (await request.get(`${api}/documents`)).json()).toEqual([])
  expect((await (await request.get(`${api}/facts`)).json()).total).toBe(0)
  expect(await (await request.get(`${api}/comparisons`)).json()).toEqual([])
  const scanPath = test.info().outputPath('scan.pdf')
  execFileSync('../backend/.venv/bin/python', ['-m', 'tests.ocr_fixtures', scanPath], { cwd: '../backend' })
  await page.locator('input[type=file]').first().setInputFiles(scanPath)
  await page.getByRole('button', { name: 'View scan.pdf', exact: true }).click()
  await expect(detail).toContainText('Revenue increased 20 percent.')
  await expect(detail).toContainText('OCR — verify against PDF')
  const scanned = (await (await request.get(`${api}/documents`)).json())[0]
  expect(scanned.status).toBe('processed')
  expect((await (await request.get(`${api}/facts?document_id=${scanned.id}`)).json()).items[0].extraction_method).toBe('ocr')
  expect(await (await request.get(`${api}/documents/${scanned.id}/source`)).body()).toEqual(readFileSync(scanPath))
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete scan.pdf', exact: true }).click()
  await expect(page.getByRole('button', { name: 'View scan.pdf', exact: true })).toHaveCount(0)
  expect(errors).toEqual([])
})
