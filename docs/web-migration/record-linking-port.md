# Porting the MHK record-linking engine to Python

Owner decision D3 (see [decisions.md](decisions.md)): the record-linking
engine of MHK — implemented as MySQL stored procedures — must be ported
to Python **inside the timelink-py package** (proposed subpackage
`timelink/linking/`), dialect-neutral for SQLite and PostgreSQL, and
later integrated with the web interface.

## Source material

Directory: `mhk/idb/etc/db/system/record_linking/` (23 files, ~280 KB
of SQL, written 2008–2009, SVN era). Test material:
`mhk/idb/etc/db/tests/record_linking/` (`tests.linking.sql`,
`tests.gtest.sql`, `LinkingTestes.sql`,
`record_linking_pre_processing1/2.sql`).

Java side: `DBSystem.processSameAs / unlinkSameAs / attach_occurence`
(`rch/DBSystem.java`) and `rch/linkingDictionary/*` are the entry
points used by the web UI; the procedures below implement the automated
*suggestion* engine behind them.

## What the engine does (conceptual model)

A classic **probabilistic record linkage** pipeline (Fellegi–Sunter
style) extended with **graph clustering** and **genealogical
consistency rules**:

1. **Pre-processing / normalization** — names are split
   (`break_name`), places and civil status normalized; relation names
   (godfather, son-of…) are mapped to pseudo-attributes
   (`relation_name_to_attributes`) so that "X is son of Y" can be
   compared as attributes of X.
2. **Value statistics** — frequency tables for attribute values
   (`values_info`), normalized values (`nvalues_info`) and attributes
   (`attributes_info`) provide agreement/disagreement ("binit")
   weights: common values discriminate less, rare values more
   (`attribute_descrim`, `avalue_nrfreq`, `avalue_prandom`...).
3. **Blocking** — `make_block` selects the small subset of persons to
   compare against a candidate (avoids O(n²)).
4. **Comparison** — `cmp_person`/`cmp_attribute` compute binit-weight
   sums for two persons.
5. **Graph expansion/generation** — `make_graph`/`fill_graph`/
   `continue_graph`/`expand_lnode` build the candidate graph
   (`lgraphs`, `candidates` clusters, `ledges` edges); edges are
   evaluated probabilistically (`eval_graph`, `reval_edges`,
   `mark_edge`) and by **non-probabilistic genealogical rules**
   (`gtest.sql`: two baptism records of same parents, burial dates
   consistent, marriage compat, self-relations…).
6. **Cluster analysis** — `clusters.sql` fragments/analyzes the graph
   (`make_clusters`, `add_to_clust`, `join_clust`, `remove_weak`…).
7. **Conversion to real entities** — confirmed clusters become real
   persons (`lgraph_to_rpersons`, `cluster_to_rperson`,
   `insert_rperson`, `insert_sameas`), scores stored in `rp_scores`
   (`calc_rperson_scores`).
8. **Queue orchestration** — `record_linking_setup` + phases 1–4 +
   `link_next`/`schedule_link` run the whole thing incrementally from
   the `link_queue` table; `llog`/`pllog` write `linklog`.

Parameters live in `syspar` (`rl.*` keys, initialized by
`linking_params_init`).

## Inventory by file

| File | Contains (procedures/functions) | Role |
|---|---|---|
| `linking_params.sql` | `linking_params_init` | `syspar` `rl.*` defaults |
| `linking_create.sql` / `linking_drop.sql` / `linking.sql` (check) | `create_linking_tables`, `drop_linking_tables`, `check_linking_structures` | DDL of linking tables |
| `names.sql` | `break_name`, `process_names`, `unprocess_names`, `plig`, `bw`? | name normalization/splitting |
| `nvalues_info.sql` | `normalize_place`, `normalize_place_names`, `normalize_civil_status`, `strip_interrog`, `count_interrog`, `init_nvalue_info`, `create_nvalue_info_table`, `set_nvalue_info`, `set_nvalue_link_info`, `update_nvalue_info`, `update_nvalues_info`, `update_nvalues_link_info`, `cont_update_nvalues_info`, `update_attribute_nvalues_info`, `avalue_nrfreq`, `avalue_npnotlink`, `avalue_prandom`, `attribute_normalization_suggestions`, `value_normalization_suggestions`, `pligp` | normalized-value frequency/weight tables |
| `values_info.sql` + `values_info_create.sql` | `create_value_info_table`, `get/set_value_info`, `update_value_info`, `update_values_info`, `update_attributes_value_info` | raw value frequency cache |
| `attributes_info.sql` | `create_attribute_info_table`, `init/update_attributes_info`, `clear_attributes_info`, `attribute_descrim`, `attribute_descrimT`, `attribute_ndescrim`, `attribute_ndescrimT`, `attribute_npersons`, `get_attribute_npersons`, `attribute_npnotlink`, `attribute_pnotlink`, `attribute_spectre`, `attribute_nspectre` | per-attribute-type statistics (discriminability, spectre) |
| `relations_info.sql` + `relations_info_create.sql` | `create_rel_equivalences_table`, `check_rel_equivalences`, `init_rel_equivalences`, `rel_equivalences` | relation-name equivalence table (data + loader) |
| `relations_to_attributes.sql` | `process_relation_names`, `process_person_relation_names`, `unprocess_relation_names`, `relation_name_to_attributes` | copy related-person attributes as pseudo-attributes |
| `make_block.sql` | `make_block`, `insert_frequent`, `insert_sameas` | blocking + seeding with known links |
| `linking.sql` | `cmp_person`, `cmp_attribute`, `cmp_attribute_old`, `insert_in_cache`, `llog`, `pllog`, `bw` | pairwise comparison + binit weights, link log |
| `gtest.sql` | `gtest`, `gtest_bapt1`, `gtest_bapt2`, `gtest_burials1`, `gtest_burials2`, `gtest_married`, `gtest_selfrel`, `make_date_standard`, `mhk_date_diff` | **genealogical consistency rules** on edges + date helpers |
| `graphs.sql` | `make_graph`, `fill_graph`, `continue_graph`, `expand_lnode`(in expand_node.sql), `eval_graph`, `pgraph`, `pgraphn`, `pgraphs`, `rm_graph`, `rm_graphn`, `remove_linked`, `suspend_graph` | graph expansion/generation phase (+ debug printers) |
| `expand_node.sql` | `expand_lnode` | single-node expansion |
| `clusters.sql` | `make_clusters`, `add_to_clust`, `join_clust`, `can_enter_clust`, `can_join_clust`, `edge_type`, `mark_edge`, `reval_edges`, `remove_weak` | cluster analysis/fragmentation |
| `graphs_to_rentities.sql` | `graph_to_rperson`, `calc_rperson_scores`, `calc_rpersons_scores`, `create_rp_scores_table` | graph ↔ real-entity interaction |
| `rentities.sql` | `insert_rperson`, `insert_rperson_with_id`, `insert_robject`, `insert_robject_with_id`, `insert_geoentity`, `remove_rperson`, `remove_robject`, `remove_geoentity`, `remove_rentity`, `remove_occurrence`, `remove_occurrence_for_user` | real-entity CRUD at SQL level |
| `identify.sql` | `record_linking_setup`, `record_linking_phase1..4`, `identify_person`, `link_next`, `schedule_link`, `slq`, `plq` | **orchestration**: phases + queue |
| `LinkingDictionaryFix.sql` | `LinkingDictionaryFix` | repair linking dictionary |

### Linking tables created

`lgraphs`, `candidates` (graph, instance, clust, status, n), `ledges`,
`link_queue`, `linklog`, `rel_equivalences`, `value_info`,
`nvalue_info`, `attribute_info` (+ cache tables), `rp_scores`. Kept in
`syspar`: `rl.*` parameters.

## Proposed Python port

New subpackage `timelink/linking/` (pure Python + SQLAlchemy, no stored
procedures), mirroring the stages:

```
timelink/linking/
├── __init__.py
├── params.py            # rl.* defaults → timelink syspar
├── normalize.py         # names.sql + nvalues_info.sql normalizers
│                        #   (break_name, normalize_place/civil_status…)
├── statistics.py        # values_info/attributes_info: frequency +
│                        #   discriminability computation (pandas-friendly)
├── relations.py         # rel_equivalences data + relations_to_attributes
├── blocking.py          # make_block
├── compare.py           # cmp_person/cmp_attribute binit weights
├── rules.py             # gtest_* genealogical rules + date helpers
├── graph.py             # make/fill/continue/eval graph, clusters
│                        #   (networkx is already a dependency)
├── rentities.py         # insert_rperson/insert_sameas equivalents —
│                        #   REUSE timelink.api.models.REntity.same_as()
├── queue.py             # link_next/identify orchestration (phases 1-4)
└── dictionary.py        # linking dictionary export/import
                         #   (productize docs/web-migration/reference/linking_dictionary.py)
```

### Suggested order (each step testable standalone)

1. **normalize.py + statistics.py + relations.py** — pure functions on
   DataFrames/ORM rows; port `tests/record_linking/pre_processing*.sql`
   fixtures to pytest. These also serve the web search page later.
2. **blocking.py + compare.py** — pairwise scoring; validate against
   hand-computed binit weights from a small test project.
3. **rules.py** (gtest) — the genealogical rules are the most
   valuable/domain-specific part; straightforward Python, heavy on
   date logic (`mhk_date_diff` → reuse `timelink/kleio/utilities.py`
   date handling where possible).
4. **graph.py** — replace `lgraphs/candidates/ledges` tables with
   networkx graphs + a persistence table pair for inspection by the
   web UI (keep a tabular projection: graph id, nodes/clusters,
   edges, status — the MHK `graph.vm` page inspects these).
5. **rentities.py + queue.py** — orchestration phases; wire
   confirm/reject actions to `REntity.same_as()`/unlink, which the web
   layer already models.
6. **dictionary.py** — export/import identifications as JSON + Kleio
   `identifications$` source (owner prototype exists).

### Notes/constraints

* Keep link ownership semantics: `links.user`, `rentities.user`,
  robot links flagged (`rule='*robot'`) — the web linking page must
  show who/what made a link.
* SQLite lacks FULLTEXT/spatial specifics — the port must not rely on
  MySQL-only functions (`MATCH...AGAINST`, `left()`, etc.).
* The `graphs.sql` debug printers (`pgraph`, `plq`) become Python
  `__repr__`/logging; the web linking page replaces them visually.
* Scoring params stay in `syspar` so users can tune from the web
  admin page exactly as MHK did.
