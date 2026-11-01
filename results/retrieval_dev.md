# bge-m3 retrieval on dev (18 answerable questions)

hit@1 = gold part ranked first, recall@5 = gold part in the top 5, MRR@10. Each question is searched in the version given in its row.

| questions | hit@1 | recall@5 | MRR@10 |
|---|---|---|---|
| all | 12/18 (67%) | 13/18 (72%) | 0.701 |
| type: adversarial | 1/2 (50%) | 2/2 (100%) | 0.750 |
| type: exact_reference | 1/3 (33%) | 1/3 (33%) | 0.370 |
| type: ordinary | 7/10 (70%) | 7/10 (70%) | 0.700 |
| type: version | 3/3 (100%) | 3/3 (100%) | 1.000 |
| wording: everyday | 2/6 (33%) | 3/6 (50%) | 0.417 |
| wording: legal | 10/12 (83%) | 10/12 (83%) | 0.843 |

## Wording pairs (recall@5, the same question asked in legal and in everyday words)

| legal found | everyday found | only legal | only everyday | pairs |
|---|---|---|---|---|
| 5 | 2 | 3 | 0 | 5 |

## Per question

| id | type | wording | gold | rank of gold | top 3 |
|---|---|---|---|---|---|
| dev-001 | ordinary | legal | 488(1) | 1 | 488(1), 48(3), 48(1) |
| dev-002 | ordinary | everyday | 488(1) | 1 | 488(1), 48(3), 374(1) |
| dev-003 | exact_reference | legal | 416(6) | 1 | 416(6), 424(6), 424(5) |
| dev-004 | version | legal | 99(1) | 1 | 99(1), 99(3), 96(2) |
| dev-006 | adversarial | legal | 95(1) | 1 | 95(1), 95(5), 95(3) |
| dev-007 | ordinary | legal | 484(1) | 1 | 484(1), 168(3), 484(2) |
| dev-008 | ordinary | everyday | 484(1) | 1 | 484(1), 486(1), 488(1) |
| dev-009 | ordinary | legal | 108 | 1 | 108, 109, 152(1) |
| dev-010 | ordinary | everyday | 108 | not in top 10 | 130(6), 215(3), 248(6) |
| dev-011 | ordinary | legal | 507-1 | 1 | 507-1, 507, 508 |
| dev-012 | ordinary | everyday | 507-1 | not in top 10 | 71(2), 420(4), 508 |
| dev-013 | ordinary | legal | 424(3) | 1 | 424(3), 424(2), 430 |
| dev-014 | ordinary | everyday | 424(3) | not in top 10 | 424(6), 424(1), 422(3) |
| dev-015 | exact_reference | legal | 419-1(1) | not in top 10 | 79-1(2), 79-1(1), 51(3) |
| dev-016 | exact_reference | legal | 346(1) | 9 | 346(3), 346(18), 346(16) |
| dev-017 | version | legal | 314(1) | 1 | 314(1), 314(3), 314(5) |
| dev-018 | version | legal | 547(1) | 1 | 547(1), 547(2), 136(1) |
| dev-020 | adversarial | everyday | 446(4) | 2 | 442(3), 446(4), 442(1) |

## Time (measured, bge-m3 loaded, qwen3:8b not loaded)

Median time per question: 19.7 ms.
