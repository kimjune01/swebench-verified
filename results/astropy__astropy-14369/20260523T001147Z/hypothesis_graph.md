# Hypothesis graph: astropy__astropy-14369

## H₀ (Abduction, Round 1)
**Claim**: The CDS format parser fails to correctly parse chained division operators, treating them as right-associative instead of left-associative.

**Evidence**:
- Test failure: `km/s/Mpc` parses as `km Mpc / s` but should parse as `km / (Mpc s)` (equivalent to `km / s / Mpc`)
- Test failure: `10+3J/m/s/kpc2` parses as `1000 J s / (kpc2 m)` with `s` in numerator, but should have `s` in denominator
- Test failure: `km/s.Mpc-1` should raise ValueError but currently parses (incorrectly as `km Mpc / s`)

**Root cause**: 
The grammar rule in `astropy/units/format/cds.py` line 185 defines:
```python
division_of_units : unit_expression DIVISION combined_units
```
By allowing `combined_units` on the right side of division, it permits recursive division parsing that associates right: `km/s/Mpc` → `km / (s/Mpc)` → `km * Mpc / s`.

Similarly, line 174:
```python
product_of_units : unit_expression PRODUCT combined_units
```
Allows `combined_units` (which includes both products and divisions) on the right, enabling invalid mixing like `km/s.Mpc-1`.

**Confidence**: Deduction — 98%
The grammar rules directly determine associativity. Right-associativity for division is mathematically wrong since `a/b/c ≠ a/(b/c)`.

**Fix**: Change grammar rules to:
1. Make division left-associative by restricting right operand to `unit_expression` and adding recursive `division_of_units DIVISION unit_expression` rule
2. Change product rule from `PRODUCT combined_units` to `PRODUCT product_of_units` to prevent mixing

## Craft: Gate loop

### Iteration 1

**Action**: Changed grammar rules in `astropy/units/format/cds.py`:
1. `p_product_of_units`: Changed right side from `combined_units` to `product_of_units` (line 173)
2. `p_division_of_units`: Changed to left-associative by:
   - Restricting binary division right side to `unit_expression` (line 183)
   - Adding recursive left case `division_of_units DIVISION unit_expression` (line 184)
3. Deleted cached parser table `cds_parsetab.py` to force regeneration

**Codex review**: Approved core grammar direction, noted action code was overcomplicated but semantically equivalent after simplification

**Gate result**: ✅ PASSED all 738 tests including all 3 FAIL_TO_PASS:
- `test_cds_grammar[strings4-unit4]`: `km/s/Mpc` now parses as `km / s / Mpc` (left-associative)
- `test_cds_grammar[strings6-unit6]`: `10+3J/m/s/kpc2` now parses as `1000 W / (m * kpc²)` (left-associative)
- `test_cds_grammar_fail[km/s.Mpc-1]`: Mixed operators now correctly raise ValueError

**Outcome**: Resolution achieved. Division is now left-associative and mixing `.` and `/` operators is rejected by the grammar.

## Audit (Round 1)

**Gate run**: All 738 tests passed on patched code.

### FAIL_TO_PASS results
- `test_cds_grammar[strings4-unit4]`: ✅ PASS — `km/s/Mpc` now parses correctly
- `test_cds_grammar[strings6-unit6]`: ✅ PASS — `10+3J/m/s/kpc2` now parses correctly  
- `test_cds_grammar_fail[km/s.Mpc-1]`: ✅ PASS — Mixed operators correctly raise ValueError

### PASS_TO_PASS regressions
none

### Pre-existing failures (confirmed against base capture)
none

**Classification**: All 3 FAIL_TO_PASS tests now pass. Zero regressions introduced. The craft patch correctly fixed the associativity issue and mixed-operator detection without breaking any existing tests.

**Verdict**: RESOLVED
**Route**: none (fix complete)
