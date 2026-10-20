# Theoretical background

`nexttext` is a lightweight toolkit for neutralizing text and generating
controlled bias for testing AI pipelines. This page explains the assumptions
behind that sentence: which kinds of bias the library can touch, why lexical
replacement is a narrow intervention, what "neutral" can mean in practice, and
when controlled bias injection is ethically defensible.

The short version is that surface-form rewriting is useful and testable, but it
is **not** a fairness method. The library changes words. It does not remove the
associations, histories, or institutional decisions that make those words
matter.

## 1. "Bias" is not one thing

Research on bias in natural language processing uses the same word for several
different problems. Blodgett et al. (2020) show that papers often conflate
harmful stereotypes, representational gaps, allocative harms, and technical
artifacts without saying which one they mean. That matters because a method
that addresses one problem can leave another untouched.

A coarse map of the space:

| Source or type | Example | What `nexttext` can do | What it cannot do |
| --- | --- | --- | --- |
| Lexical gender marking | `man`, `woman`, `he`, `her`, gendered job titles | Replace matched words and phrases with neutral forms | Decide whether a particular mention should be neutralized |
| Pronoun and agreement | `he runs` → `they run` | Apply lexical or optional dependency-aware rules | Resolve all coreference or produce fully grammatical text |
| Stereotypical associations | `doctor` co-occurring with `he`, `nurse` with `she` | Expose and vary associations with keyword-driven rebiasing | Remove learned associations from a model or dataset |
| Representational bias | Fewer examples of women in a dataset | Make surface statistics easier to inspect | Fix sampling, labeling, or collection practices |
| Historical and institutional bias | Labels that encode past hiring or policing decisions | Nothing structural | Change the process that produced the labels |
| Allocative or outcome bias | A system that grants loans unevenly | Nothing | Serve as a compliance or fairness audit |

The library is deliberately positioned at the first two rows. Its benchmark
measures whether rewrites introduce grammar errors, not whether a model or
dataset has become fair.

## 2. Why lexical replacement is limited

The default path uses curated maps and regular expressions. That design keeps
the package small, inspectable, deterministic, and dependency-free. It also
imposes hard limits.

### 2.1 Word sense and names

A string such as `man` can be a common noun, a name, part of a title, or an
idiom. `nexttext` cannot reliably tell these apart. Callers can protect exact
proper nouns, and the optional `nlp` strategy uses part-of-speech information
to avoid some multi-token names, but neither approach resolves word sense in
general. The documentation recommends reviewing output rather than assuming
that every replacement is correct.

### 2.2 Coreference and agreement

Replacing `he` with `they` changes the grammatical number of the subject.
English verbs, reflexives, and possessives may then need to change as well.
The default strategy handles a small set of frequent forms; the optional
`nlp` strategy uses dependency information for subject-verb agreement and
possessive versus object `her`. Neither strategy performs full coreference
resolution. A sentence with several possible antecedents can still become
ambiguous after rewriting (Zhao et al., 2018; Rudinger et al., 2018).

### 2.3 Semantic loss and ambiguity

Neutralization can delete information that a reader or a downstream model
needs. `"Madame Curie was a woman ahead of her time"` becomes less specific
when `woman` is replaced. `"The man gave the boy his ball"` already has an
ambiguous possessive; replacing both people with neutral terms can make the
ambiguity harder to notice. Surface neutrality is not semantic equivalence.

### 2.4 Associations survive the rewrite

Word-embedding studies show that gendered associations are widespread and
systematic (Bolukbasi et al., 2016; Caliskan et al., 2017). Gonen and Goldberg
(2019) show that common debiasing procedures can hide those associations from a
particular probe without removing them from the representation. A lexical
rewrite is even weaker: it changes the observable string while leaving the
model, the training data, and the surrounding discourse untouched. Removing a
word is not the same as removing a stereotype.

### 2.5 Binary and non-binary representation

Most English gender resources are binary. Replacing `he` and `she` with
`they` can make a sentence less binary, but it can also erase a person's
self-described identity or imply that gender is an optional detail. Dev et al.
(2021) document harms that arise when language technologies treat gender as a
simple male/female switch. `nexttext` provides configurable lexicons and
neopronoun mappings so that callers can encode a different policy, but the
default map is still a policy choice, not a neutral fact.

### 2.6 The pipeline is larger than the string

Bias can enter through data collection, annotation instructions, label
aggregation, model architecture, evaluation metrics, and deployment decisions
(Hovy & Prabhumoye, 2021). A text-rewriting function sees only one string at
one moment. It cannot inspect who was excluded from a dataset, how a label was
produced, or what a system does with the output.

## 3. What "neutral" can and cannot mean

`nexttext` uses "neutral" in a narrow, operational sense:

- **Can mean:** the output no longer contains the specific gendered terms that
  the active lexicon maps to neutral replacements.
- **Can mean:** the output is easier to inspect for surface-level skew, and it
  gives a reproducible baseline for experiments.
- **Cannot mean:** the output is objective, unbiased, or free of connotations.
- **Cannot mean:** the output preserves meaning, especially for names,
  coreference, idioms, or identity terms.
- **Cannot mean:** the output is appropriate for every audience or locale. The
  built-in resources are English and predominantly binary.

Neutral wording is a design decision. Choosing `person` instead of `man` or
`woman` foregrounds some information and backgrounds other information. That
can be the right choice for a captioning dataset; it can be the wrong choice
for a quote, a legal record, or a user profile. The library should therefore be
used with an explicit policy and human review, not as an automatic correctness
layer.

## 4. The ethics of controlled stereotype injection

`rebias` and its explicit test-oriented alias `inject_bias` deliberately put
gendered language back into neutral text. That is a legitimate technique when
the goal is to test whether a pipeline is robust to skew, but it is easy to
misuse.

Defensible uses:

- Building paired test cases, such as a neutral caption and a masculine or
  feminine variant, to measure whether a classifier's behavior changes.
- Red-teaming a retrieval, ranking, or generation pipeline in a sandbox.
- Teaching how keyword-driven heuristics behave, including their failure modes.
- Producing synthetic evaluation data that is clearly labeled as synthetic.

Indefensible uses:

- Generating deceptive or harassing content about real people.
- Producing high-stakes material (medical, legal, financial, safety) without
  expert review.
- Claiming that an injected-stereotype dataset is representative of a
  population.
- Using "it was only a test" to avoid consent, licensing, or review
  requirements for the underlying data.

Practical safeguards:

1. Keep injected data separate from production data and label it with its
   provenance.
2. Do not present generated stereotypes as facts or as descriptions of real
   individuals.
3. Check the license and consent terms of the source text before creating
   variants.
4. Measure both intended effects and collateral damage; a robustness test that
   only looks for the effect it hopes to find is not a test.
5. Route consequential decisions to humans. The library provides annotations
   and confidence scores, not approvals.

## 5. What the benchmark does and does not show

The `0.3.0` and `0.4.0` benchmarks use LanguageTool to count captions whose
rewritten form has more grammar matches than the original. That is a
reproducible proxy for fluency, not a bias metric. It does not measure whether
a stereotype was removed, whether meaning was preserved, or whether a model is
fair. The `0.4.0` decision memo adds an embedding-similarity measurement, but
cosine similarity is also a coarse proxy for topical overlap.

Treat the numbers as evidence about engineering behavior: which rules fire, how
often they break agreement, and what an optional backend costs. Do not treat
them as evidence of social impact.

## 6. Design consequences

The theory above leads to a few product rules:

- Keep the default path small and deterministic so that its behavior is easy to
  audit.
- Make optional backends opt-in and never describe them as fairness fixes.
- Expose confidence, rule hits, and `flag_only` so that callers can review
  changes instead of trusting them.
- Document misuse cases next to the features, not in a separate policy page
  that users never read.
- Prefer reproducible benchmarks over claims. If a backend cannot show a
  measurable improvement, do not promote it to the default path.

## References

- Bender, E. M., Gebru, T., McMillan-Major, A., & Shmitchell, S. (2021). On the
  Dangers of Stochastic Parrots: Can Language Models Be Too Big? *FAccT '21*,
  610-623. <https://doi.org/10.1145/3442188.3445922>
- Blodgett, S. L., Barocas, S., Daumé III, H., & Wallach, H. (2020). Language
  (Technology) is Power: A Critical Survey of "Bias" in NLP. *ACL 2020*,
  5454-5476. <https://arxiv.org/abs/2005.14050>
- Bolukbasi, T., Chang, K.-W., Zou, J., Saligrama, V., & Kalai, A. (2016). Man
  is to Computer Programmer as Woman is to Homemaker? Debiasing Word
  Embeddings. *NeurIPS 29*. <https://arxiv.org/abs/1607.06520>
- Caliskan, A., Bryson, J. J., & Narayanan, A. (2017). Semantics derived
  automatically from language corpora contain human-like biases. *Science*,
  356(6334), 183-186. <https://doi.org/10.1126/science.aal4230>
- Dev, S., Monajatipoor, M., Ovalle, A., Subramonian, A., Phillips, J. M., &
  Chang, K.-W. (2021). Harms of Gender Exclusivity and Challenges in Non-Binary
  Representation in Language Technologies. *EMNLP 2021*, 1968-1994.
  <https://arxiv.org/abs/2108.12084>
- Gonen, H., & Goldberg, Y. (2019). Lipstick on a Pig: Debiasing Methods Cover
  up Systematic Gender Biases in Word Embeddings But do not Remove Them.
  *NAACL-HLT 2019*, 609-614. <https://arxiv.org/abs/1903.03862>
- Hovy, D., & Prabhumoye, S. (2021). Five sources of bias in natural language
  processing. *Language and Linguistics Compass*, 15(8), e12432.
  <https://doi.org/10.1111/lnc3.12432>
- Rudinger, R., Naradowsky, J., Leonard, B., & Van Durme, B. (2018). Gender
  Bias in Coreference Resolution. *NAACL-HLT 2018*, 8-14.
  <https://arxiv.org/abs/1804.09301>
- Sun, T., Gaut, A., Tang, S., Huang, Y., & Chang, K.-W. (2019). Mitigating
  Gender Bias in Natural Language Processing: Literature Review. *ACL 2019*,
  1630-1640. <https://arxiv.org/abs/1906.08976>
- Zhao, J., Wang, T., Yatskar, M., Ordonez, V., & Chang, K.-W. (2018). Gender
  Bias in Coreference Resolution: Evaluation and Debiasing Methods.
  *NAACL-HLT 2018*, 15-20. <https://arxiv.org/abs/1804.06876>
