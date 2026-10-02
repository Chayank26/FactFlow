import { test, expect } from '@playwright/test'
import { existsSync } from 'node:fs'

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
const navigate = (page, name) => page.getByRole('navigation', { name: 'Workspace' }).getByRole('link', { name, exact: true }).click()

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
  await expect(detail.locator('.fact-row span').first()).toContainText('Page 1')
  const second = await upload('second.pdf', claims[0])
  await navigate(page, 'Facts')
  await page.getByRole('combobox', { name: 'Source' }).selectOption(first.id)
  await page.getByRole('textbox', { name: 'Search' }).fill('metric 24')
  await expect(page.locator('.fact-browser-card')).toHaveCount(1)
  await expect(page.locator('.fact-browser-card')).toContainText(claims[24])
  await navigate(page, 'Comparisons')
  await page.getByRole('combobox', { name: 'Source' }).selectOption(second.id)
  await page.getByRole('combobox', { name: 'Relationship' }).selectOption('agreement')
  await expect(page.locator('.comparison-card')).toHaveCount(1)
  await expect(page.locator('.comparison-card')).toContainText('Matching wording')
  await expect(page.locator('.comparison-card')).toContainText('first.pdf')
  await expect(page.locator('.comparison-card')).toContainText('second.pdf')
  await navigate(page, 'Documents')
  const before = await (await request.get(`${api}/facts?document_id=${first.id}`)).json()
  const processed = page.waitForResponse(response => response.url().endsWith(`/documents/${first.id}/process`))
  await page.getByRole('button', { name: 'Reprocess first.pdf', exact: true }).click()
  expect((await processed).ok()).toBe(true)
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
  expect(errors).toEqual([])
})
