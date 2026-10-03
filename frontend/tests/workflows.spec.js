import { test, expect } from '@playwright/test'

// Controlled API responses test browser behavior without touching local data.
// Real PDF parsing, storage, and API contracts are covered by backend pytest.
async function setup(page, { empty = false } = {}) {
  const doc = id => ({ id, filename: `${id}.pdf`, size_bytes: 100, content_type: 'application/pdf', stored_path: '', created_at: '2026-09-28T00:00:00Z', status: 'processed' })
  const state = { docs: empty ? [] : [doc('alpha'), doc('beta')], count: 65, fail: '', busy: false, requests: [] }
  page.on('pageerror', error => { throw error })
  await page.route('http://127.0.0.1:8019/**', async route => {
    const request = route.request()
    const url = new URL(request.url())
    state.requests.push({ path: url.pathname, query: url.searchParams, method: request.method() })
    if (state.busy && ['POST', 'DELETE'].includes(request.method())) {
      return route.fulfill({ status: 503, headers: { 'Retry-After': '1' }, json: { detail: 'Operation in progress' } })
    }
    if (state.fail === url.pathname) {
      return route.fulfill({ status: 500, json: { detail: 'Simulated failure' } })
    }
    let body
    if (url.pathname === '/health') body = { status: 'ok', service: 'fact-layer-api' }
    else if (url.pathname === '/documents' && request.method() === 'POST') {
      expect(request.headers()['content-type']).toContain('multipart/form-data')
      expect(request.postDataBuffer().toString()).toContain('upload.pdf')
      const created = doc('upload'); state.docs.unshift(created); body = created
    } else if (url.pathname === '/documents') {
      const items = state.docs.filter(document => document.filename.includes(url.searchParams.get('search') || ''))
      const offset = Number(url.searchParams.get('offset') || 0)
      const limit = Number(url.searchParams.get('limit') || 50)
      body = { items: items.slice(offset, offset + limit), total: items.length, limit, offset }
    }
    else if (url.pathname.endsWith('/process')) { state.count = 3; body = state.docs[0] }
    else if (request.method() === 'DELETE') {
      state.docs = state.docs.filter(document => url.pathname !== `/documents/${document.id}`)
      return route.fulfill({ status: 204 })
    } else if (url.pathname.startsWith('/documents/')) body = state.docs.find(document => url.pathname === `/documents/${document.id}`)
    else if (url.pathname === '/facts') {
      const id = url.searchParams.get('document_id') || 'alpha'
      const search = url.searchParams.get('search') || ''
      const total = search === 'missing' ? 0 : id === 'beta' ? 1 : state.count
      const offset = Number(url.searchParams.get('offset') || 0)
      const limit = Number(url.searchParams.get('limit') || 50)
      body = { total, offset, limit, items: Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, i) => ({ id: `${id}-${offset+i}`, document_id: id, claim: `${id} evidence ${offset+i}`, source_page: 1, source_text: `source ${offset+i}`, created_at: '2026-09-28T00:00:00Z' })) }
    } else if (url.pathname === '/comparisons') {
      body = ['agreement', 'difference'].filter(relationship => !url.searchParams.get('relationship') || relationship === url.searchParams.get('relationship')).map(relationship => ({ id: relationship, relationship, summary: 'Review both passages.', left_document_id: 'alpha', left_document_name: 'alpha.pdf', left_claim: 'Revenue increased 20 percent.', left_page: 1, left_source_text: 'Left source passage', right_document_id: 'beta', right_document_name: 'beta.pdf', right_claim: 'Revenue increased 30 percent.', right_page: 2, right_source_text: 'Right source passage' }))
    } else throw new Error(`Unexpected API request: ${request.method()} ${url}`)
    if (url.pathname === '/comparisons') {
      const offset = Number(url.searchParams.get('offset') || 0)
      const limit = Number(url.searchParams.get('limit') || 50)
      body = { items: body.slice(offset, offset + limit), total: body.length, offset, limit }
    }
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
    await expect(page.getByRole('alert').filter({ hasText: `${view} could not be loaded` })).toBeVisible()
    await expect(page.locator('.stat-card').filter({ hasText: view }).locator('.stat-number')).toHaveText('—')
  }
  state.fail = ''
  await navigate(page, 'Facts')
  await expect(page.getByText('Showing 1–20 of 65')).toBeVisible()
})

test('processing notice persists across navigation and failure unlocks retry', async ({ page }) => {
  const state = await setup(page)
  let finish
  const gate = new Promise(resolve => { finish = resolve })
  await page.route('**/documents/alpha/process', async route => {
    await gate
    state.docs[0].status = 'extraction_failed'
    await route.fulfill({ status: 422, json: { detail: 'Simulated processing failure' } })
  })
  try {
    await page.goto('/')
    await page.getByRole('button', { name: 'View alpha.pdf', exact: true }).click()
    await expect(page.getByText('Showing 1–20 of 65')).toBeVisible()
    await page.getByRole('button', { name: 'Reprocess alpha.pdf', exact: true }).click()
    await expect(page.locator('.processing-notice')).toContainText('Reprocessing alpha.pdf')
    await expect(page.getByRole('button', { name: 'Reprocess alpha.pdf', exact: true })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Delete alpha.pdf', exact: true })).toBeDisabled()
    await expect(page.locator('input[type=file]').first()).toBeDisabled()
    await navigate(page, 'Facts')
    await expect(page.locator('.processing-notice')).toBeVisible()
    await navigate(page, 'Documents')
    finish()
    await expect(page.getByRole('alert')).toContainText('Reprocessing failed')
    await expect(page.locator('.processing-notice')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Reprocess alpha.pdf', exact: true })).toBeEnabled()
    await page.unroute('**/documents/alpha/process')
    let succeed
    const successGate = new Promise(resolve => { succeed = resolve })
    await page.route('**/documents/alpha/process', async route => {
      await successGate
      state.docs[0].status = 'processed'
      state.count = 3
      await route.fulfill({ json: state.docs[0] })
    })
    await page.getByRole('button', { name: 'Reprocess alpha.pdf', exact: true }).click()
    await navigate(page, 'Facts')
    await expect(page.getByText('Showing 1–20 of 65')).toBeVisible()
    succeed()
    await expect(page.getByText('Showing 1–3 of 3')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Facts', exact: true })).toBeVisible()
    await navigate(page, 'Documents')
    await expect(page.getByRole('alert')).toHaveCount(0)
    await expect(page.locator('.processing-notice')).toHaveCount(0)
  } finally {
    finish()
  }
})

test('document and comparison pages stay bounded and later sources are selectable', async ({ page }) => {
  const state = await setup(page)
  state.docs = Array.from({ length: 25 }, (_, i) => ({ ...state.docs[0], id: `doc${i}`, filename: `source-${String(i).padStart(2, '0')}.pdf` }))
  await page.route('**/comparisons?*', async route => {
    const url = new URL(route.request().url())
    const all = Array.from({ length: 45 }, (_, i) => ({ id: String(i), relationship: i % 2 ? 'agreement' : 'difference', summary: 'Review sources', left_document_id: 'doc0', right_document_id: 'doc24', left_document_name: 'source-00.pdf', right_document_name: 'source-24.pdf', left_claim: `Claim ${i}`, right_claim: `Other ${i}`, left_source_text: 'First passage', right_source_text: 'Second passage', left_page: 1, right_page: 2 })).filter(item => !url.searchParams.get('relationship') || item.relationship === url.searchParams.get('relationship'))
    const offset = Number(url.searchParams.get('offset'))
    const limit = Number(url.searchParams.get('limit'))
    await route.fulfill({ json: { items: all.slice(offset, offset + limit), total: all.length, offset, limit } })
  })
  await page.goto('/')
  await expect(page.locator('.document-card')).toHaveCount(20)
  await page.getByRole('button', { name: 'Next documents', exact: true }).click()
  await expect(page.locator('.document-card')).toHaveCount(5)
  await expect(page.getByRole('button', { name: 'View source-24.pdf', exact: true })).toBeVisible()
  await expect(page.locator('.stat-card').filter({ hasText: 'Documents' }).locator('.stat-number')).toHaveText('25')
  await navigate(page, 'Facts')
  await page.getByRole('button', { name: 'Next sources', exact: true }).click()
  await page.getByRole('combobox', { name: 'Source', exact: true }).selectOption('doc24')
  await expect.poll(() => state.requests.some(request => request.path === '/facts' && request.query.get('document_id') === 'doc24')).toBe(true)
  await page.getByRole('textbox', { name: 'Find source by filename' }).fill('source-03')
  await page.getByRole('combobox', { name: 'Source', exact: true }).selectOption('doc3')
  await navigate(page, 'Comparisons')
  await expect(page.locator('.comparison-card')).toHaveCount(20)
  await page.getByRole('button', { name: 'Next comparisons', exact: true }).click()
  await expect(page.getByText('Showing 21–40 of 45 comparisons')).toBeVisible()
  await page.getByRole('button', { name: 'Next comparisons', exact: true }).click()
  await expect(page.locator('.comparison-card')).toHaveCount(5)
  await expect(page.getByRole('button', { name: 'Next comparisons', exact: true })).toBeDisabled()
  await page.getByRole('combobox', { name: 'Relationship' }).selectOption('agreement')
  await expect(page.getByText('Showing 1–20 of 22 comparisons')).toBeVisible()
  await expect(page.locator('.stat-card').filter({ hasText: 'Comparisons' }).locator('.stat-number')).toHaveText('22')
})


test('busy mutations retain evidence and allow explicit retry', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'View alpha.pdf', exact: true }).click()
  await expect(page.locator('.document-detail .fact-row')).toHaveCount(20)
  state.busy = true
  const file = { name: 'upload.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF test') }
  await page.locator('input[type=file]').first().setInputFiles(file)
  await expect(page.getByText('This upload was not started.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Reprocess alpha.pdf', exact: true }).click()
  await expect(page.getByText('This request did not change your evidence.', { exact: false })).toBeVisible()
  await expect(page.locator('.document-detail .fact-row')).toHaveCount(20)
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete alpha.pdf', exact: true }).click()
  await expect(page.getByText('This document was not deleted.', { exact: false })).toBeVisible()
  await expect(page.getByRole('button', { name: 'View alpha.pdf', exact: true })).toBeVisible()
  await navigate(page, 'Facts')
  await expect(page.locator('.fact-browser-card').first()).toBeVisible()
  expect(state.requests.filter(r => ['POST', 'DELETE'].includes(r.method))).toHaveLength(3)
  state.busy = false
  await navigate(page, 'Documents')
  await page.getByRole('button', { name: 'Reprocess alpha.pdf', exact: true }).click()
  await expect(page.getByText('This request did not change your evidence.', { exact: false })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Reprocess alpha.pdf', exact: true })).toBeEnabled()
  await page.locator('input[type=file]').first().setInputFiles(file)
  await expect(page.getByRole('button', { name: 'View upload.pdf', exact: true })).toBeVisible()
  await expect(page.getByText('This upload was not started.', { exact: false })).toHaveCount(0)
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Delete alpha.pdf', exact: true }).click()
  await expect(page.getByRole('button', { name: 'View alpha.pdf', exact: true })).toHaveCount(0)
  expect(state.requests.filter(r => ['POST', 'DELETE'].includes(r.method))).toHaveLength(6)
})
