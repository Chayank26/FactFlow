"""Exact candidate pruning for the existing textual comparison heuristic."""
from collections import defaultdict


def candidate_pairs(rows, tokenize, normalize, document_id=None):
    tokens = [tokenize(row['claim']) for row in rows]
    normalized = [normalize(row['claim']) for row in rows]
    postings = defaultdict(list)
    exact = defaultdict(list)
    for index, values in enumerate(tokens):
        if not values:
            continue
        for token in values:
            postings[token].append(index)
        exact[normalized[index]].append(index)
    for left, values in enumerate(tokens):
        if not values:
            continue
        shared = defaultdict(int)
        for token in values:
            for right in postings[token]:
                if right > left and rows[left]['document_id'] != rows[right]['document_id']:
                    if not document_id or document_id in (rows[left]['document_id'], rows[right]['document_id']):
                        shared[right] += 1
        candidates = {right for right, count in shared.items() if count >= 2}
        candidates.update(right for right in exact[normalized[left]] if right > left)
        for right in sorted(candidates):
            if rows[left]['document_id'] == rows[right]['document_id']:
                continue
            if document_id and document_id not in (rows[left]['document_id'], rows[right]['document_id']):
                continue
            if normalized[left] == normalized[right]:
                yield left, right, 'agreement'
            elif shared[right] / max(len(values), len(tokens[right])) >= 0.5:
                yield left, right, 'difference'
