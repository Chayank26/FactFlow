import { test, expect } from '@playwright/test'

// Controlled API responses test browser behavior without touching local data.
// Real PDF parsing, storage, and API contracts are covered by backend pytest.
async function setup(page, { empty = false } = {}) {
  const doc = id => ({ id, filename: `${id}.pdf`, size_bytes: 100, content_type: 'application/pdf', stored_path: '', created_at: '2026-09-28T00:00:00Z', status: 'processed' })
  const state = { docs: empty ? [] : [doc('alpha'), doc('beta')], count: 65, fail: '', requests: [] }
  page.on('pageerror', error => { throw error })
  await page.route('http://127.0.0.1:8019/**', async route => {
    const request = route.request()
    const url = new URL(request.url())
    state.requests.push({ path: url.pathname, query: url.searchParams, method: request.method() })
    if (state.fail === url.pathname) {
      return route.fulfill({ status: 500, json: { detail: 'Simulated failure' } })
    }
    let body
    if (url.pathname === '/health') body = { status: 'ok', service: 'fact-layer-api' }
    else if (url.pathname === '/documents' && request.method() === 'POST') {
      expect(request.headers()['content-type']).toContain('multipart/form-data')
      expect(request.postDataBuffer().toString()).toContain('upload.pdf')
      const created = doc('upload'); state.docs.unshift(created); body = created
    } else if (url.pathname === '/documents') body = state.docs
    else if (url.pathname.endsWith('/process')) { state.count = 3; body = state.docs[0] }
    else if (request.method() === 'DELETE') {
      state.docs = state.docs.filter(document => url.pathname !== `/documents/${document.id}`)
      return route.fulfill({ status: 204 })
    } else if (url.pathname === '/facts') {
      const id = url.searchParams.get('document_id') || 'alpha'
      const search = url.searchParams.get('search') || ''
      const total = search === 'missing' ? 0 : id === 'beta' ? 1 : state.count
      const offset = Number(url.searchParams.get('offset') || 0)
      const limit = Number(url.searchParams.get('limit') || 50)
      body = { total, offset, limit, items: Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, i) => ({ id: `${id}-${offset+i}`, document_id: id, claim: `${id} evidence ${offset+i}`, source_page: 1, source_text: `source ${offset+i}`, created_at: '2026-09-28T00:00:00Z' })) }
    } else if (url.pathname === '/comparisons') {
      body = ['agreement', 'difference'].filter(relationship => !url.searchParams.get('relationship') || relationship === url.searchParams.get('relationship')).map(relationship => ({ id: relationship, relationship, summary: 'Review both passages.', left_document_id: 'alpha', left_document_name: 'alpha.pdf', left_claim: 'Revenue increased 20 percent.', left_page: 1, left_source_text: 'Left source passage', right_document_id: 'beta', right_document_name: 'beta.pdf', right_claim: 'Revenue increased 30 percent.', right_page: 2, right_source_text: 'Right source passage' }))
    } else throw new Error(`Unexpected API request: ${request.method()} ${url}`)
    await route.fulfill({ json: body })
  })
  return state
}

const navigate = async (page, name) => {
  await page.getByRole('navigation', { name: 'Workspace' }).getByRole('link', { name, exact: true }).click()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
}

test('upload, paginate evidence, reprocess, and cancel/confirm deletion', async ({ page }) => {
  const state = await setup(page, { empty: true })
  await page.goto('/')
  await expect(page.getByText('Backend connected', { exact: true })).toBeVisible()
  await expect(page.getByText('Good knowledge starts with a source.')).toBeVisible()
  await page.locator('input[type=file]').first().setInputFiles({ name: 'upload.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 test upload') })
  await page.getByRole('button', { name: 'View upload.pdf', exact: true }).click()
  const detail = page.locator('.document-detail')
  await expect(detail.getByText('Showing 1–20 of 65')).toBeVisible()
  await expect(detail.getByRole('button', { name: 'Previous' })).toBeDisabled()
  for (const range of ['21–40', '41–60', '61–65']) {
    await detail.getByRole('button', { name: 'Next' }).click()
    await expect(detail.getByText(`Showing ${range} of 65`)).toBeVisible()
  }
  await expect(detail.getByRole('button', { name: 'Next' })).toBeDisabled()
  await detail.getByRole('button', { name: 'Previous' }).click()
  await expect(detail.getByText('Showing 41–60 of 65')).toBeVisible()
  await page.getByRole('button', { name: 'Reprocess upload.pdf', exact: true }).click()
  await expect(detail.getByText('Showing 1–3 of 3')).toBeVisible()
  page.once('dialog', dialog => dialog.dismiss())
  await page.getByRole('button', { name: 'Delete upload.pdf', exact: true }).click()
  await expect(detail).toBeVisible()
  expect(state.requests.filter(request => request.method === 'DELETE')).toHaveLength(0)
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete upload.pdf', exact: true }).click()
  await expect(detail).toHaveCount(0)
  await expect(page.getByText('Good knowledge starts with a source.')).toBeVisible()
})

test('facts paginate, filters reset the page, and navigation survives reload/back', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/')
  await navigate(page, 'Facts')
  await expect(page.getByText('Showing 1–20 of 65')).toBeVisible()
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  await expect(page.getByText('Showing 21–40 of 65')).toBeVisible()
  await page.getByRole('combobox', { name: 'Source' }).selectOption('beta')
  await expect(page.getByText('Showing 1–1 of 1')).toBeVisible()
  await page.getByRole('textbox', { name: 'Search' }).fill('missing')
  await expect(page.getByText('No matching facts.')).toBeVisible()
  await expect(page.locator('.stat-card').filter({ hasText: 'Facts' }).locator('.stat-number')).toHaveText('0')
  await expect(page.locator('.stat-card').filter({ hasText: 'Facts' })).toContainText('Results for current filters')
  expect(state.requests.some(request => request.query.get('search') === 'missing' && request.query.get('document_id') === 'beta' && request.query.get('offset') === '0')).toBe(true)
  await page.getByRole('textbox', { name: 'Search' }).fill('')
  await expect(page.getByText('Showing 1–1 of 1')).toBeVisible()
  await navigate(page, 'Comparisons')
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Facts', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Facts', exact: true })).toBeVisible()
  await expect(page.getByText('Coming soon', { exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('comparison filters retain source evidence and cautious labels', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/#comparisons')
  await expect(page.locator('.comparison-card')).toHaveCount(2)
  await page.getByRole('combobox', { name: 'Source' }).selectOption('alpha')
  await page.getByRole('combobox', { name: 'Relationship' }).selectOption('difference')
  await expect(page.locator('.comparison-card')).toHaveCount(1)
  await expect(page.locator('.relationship-label')).toHaveText('Possible difference')
  await expect(page.getByText('Page 2 · Right source passage')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Open PDF · page 2 (new tab)' })).toHaveAttribute('href', 'http://127.0.0.1:8019/documents/beta/source#page=2')
  expect(state.requests.some(request => request.query.get('document_id') === 'alpha' && request.query.get('relationship') === 'difference')).toBe(true)
  await page.getByRole('combobox', { name: 'Relationship' }).selectOption('agreement')
  await expect(page.locator('.relationship-label')).toHaveText('Matching wording')
})

test('health, upload, evidence, and list failures are visible and recoverable', async ({ page }) => {
  const state = await setup(page)
  state.fail = '/health'
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Retry connection' })).toBeVisible()
  state.fail = ''
  await page.getByRole('button', { name: 'Retry connection' }).click()
  await expect(page.getByText('Backend connected', { exact: true })).toBeVisible()
  state.fail = '/documents'
  await page.locator('input[type=file]').first().setInputFiles({ name: 'upload.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 test') })
  await expect(page.getByText('The upload could not be saved. Please try again.')).toBeVisible()
  state.fail = '/facts'
  await page.getByRole('button', { name: 'View alpha.pdf', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Retry evidence' })).toBeVisible()
  state.fail = ''
  await page.getByRole('button', { name: 'Retry evidence' }).click()
  await expect(page.getByText('Showing 1–20 of 65')).toBeVisible()
  await page.getByRole('button', { name: 'View beta.pdf', exact: true }).click()
  await expect(page.getByText('Showing 1–1 of 1')).toBeVisible()
  for (const [path, view] of [['/facts', 'Facts'], ['/comparisons', 'Comparisons'], ['/documents', 'Documents']]) {
    state.fail = path
    await navigate(page, view)
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.locator('.stat-card').filter({ hasText: view }).locator('.stat-number')).toHaveText('—')
  }
  state.fail = ''
  await navigate(page, 'Facts')
  await expect(page.getByText('Showing 1–20 of 65')).toBeVisible()
})
