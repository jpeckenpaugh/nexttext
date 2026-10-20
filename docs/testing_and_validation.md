# nexttext: Testing and Validation Plan

> `nexttext` is a lightweight toolkit for neutralizing text and generating
> controlled bias for testing AI pipelines. This plan describes how the
> library's rewrites are measured; it is not a fairness certification. See
> [`theoretical_background.md`](theoretical_background.md) for the scope and
> limits of the metrics.

## 1. Overview and Goals

This document outlines the standardized process for testing, validating, and benchmarking the `nexttext` library. The primary goal is not to achieve 100% accuracy, but to **quantify the performance** of the library's heuristic-based approach on real-world data, starting with version `0.0.1`.

The core principles of this plan are:
-   **Data-Driven:** All benchmarks will be run against large, public datasets to reflect real-world usage.
-   **Independent Validation:** We will use third-party tools to grade the grammatical and semantic correctness of the output, avoiding confirmation bias.
-   **Transparency:** The results of these benchmarks will be published with each release to track progress and honestly communicate the library's capabilities and limitations.
-   **Iterative Improvement:** The validation process is designed to create a continuous feedback loop, where identified failures become the basis for the next development cycle.

---

## 2. The Benchmark Dataset

To ensure our testing is relevant, we will use a standardized sample of captions from a well-known image captioning dataset.

-   **Source Dataset:** **MS-COCO Captions** (via the `jxie/coco_captions` Hugging Face dataset).
-   **Sampling Method:** We will stream the dataset and filter for the first **1,000 captions** that contain at least one person-related keyword. This creates a challenging and relevant test set for our `debias` function.
-   **Reproducibility:** The sampling script will be maintained in the repository to ensure that the exact same test set is used for every release benchmark, guaranteeing comparable results over time.

---

## 3. The Independent Validation Tool

To "grade our own homework," we need an automated, independent tool to check the grammatical validity of the debiased output.

-   **Primary Tool:** **`language-tool-python`**.
-   **Function:** This library will be used to programmatically scan each debiased sentence for grammatical errors, such as incorrect subject-verb agreement, which are likely side effects of simple term replacement.
-   **Metric:** The primary benchmark metric will be the **"Grammatical Error Rate,"** defined as the percentage of processed sentences that contain one or more new grammatical errors after debiasing.

---

## 4. Known Edge Cases for `v0.0.1`

The current heuristic-based `debias` function is not expected to handle all linguistic complexities. This benchmark will specifically measure its performance against the following known challenges:

1.  **Subject-Verb Agreement:**
    -   **Description:** The most common failure mode. Replacing a singular pronoun with a plural one often invalidates the verb form.
    -   **Example:** "He **runs**" -> "They **runs**" (Incorrect). The correct output is "They **run**."

2.  **Conjoined Noun Phrase Aggregation:**
    -   **Description:** The system cannot combine multiple, distinct noun phrases into a single, cohesive one after neutralization.
    -   **Example:** "Two boys and a girl" -> "Two children and a child" (Awkward). The ideal output is "Three children."

3.  **Loss of Necessary Context:**
    -   **Description:** In some cases, removing gender erases essential historical or semantic context, making the sentence less meaningful.
    -   **Example:** "Madame Curie was a woman ahead of her time" -> "Person Curie was a person ahead of their time" (Loss of meaning).

4.  **Possessive Ambiguity:**
    -   **Description:** While "their" is a correct neutral possessive, it can sometimes create ambiguity that "his" or "her" did not have. This is not a grammatical error but a semantic one.
    -   **Example:** "The man gave the boy his ball." (Unambiguous: the man's ball). -> "The person gave the child their ball." (Ambiguous: whose ball is it?).

---

## 5. The v0.0.1 Benchmarking Process

The following steps will be executed to establish the initial performance benchmark for the `v0.0.1` release.

1.  **Sample the Data:** Run the sampling script to generate the `coco_benchmark_1000.txt` file containing 1,000 person-related captions.
2.  **Process with `nexttext`:** Feed the 1,000 captions into the `nexttext.debias` function and save the output.
3.  **Validate with LanguageTool:** Run a validation script that iterates through each original/debiased pair and uses `language_tool_python` to check for grammatical errors in the **debiased** version.
4.  **Quantify Results:** The script will output a summary report with:
    -   Total sentences processed.
    -   Number of sentences flagged with grammatical errors.
    -   The final **Grammatical Error Rate (%)**.
5.  **Categorize Failures:** Manually review the first 50 flagged errors and categorize them according to the edge cases listed in Section 4. This will provide a clear direction for the `v0.0.2` development cycle.
6.  **Publish Results:** Commit the summary report to the repository as `docs/benchmarks/v0.0.1_report.md`.

---

## 6. Heuristic Improvement Cycle & Future Development

This benchmark is the starting point for a continuous improvement cycle.

-   **From Failures to Features:** The most common failure category from the `v0.0.1` benchmark will become the top priority for `v0.0.2`. For example, if subject-verb agreement is the biggest issue, new heuristics will be developed to address it.
-   **Confidence Scoring:** Future versions will implement a "confidence score" for each transformation. Sentences that trigger known complex edge cases (like conjoined nouns) will receive a lower score.
-   **User Strategies:** Users will be able to set a confidence threshold and choose a `strategy` (e.g., `exclude`, `flag_for_review`) to decide how the library should handle low-confidence transformations, making it safe for production pipelines.
