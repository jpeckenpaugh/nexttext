'''
nexttext_benchmark_v0.0.1.py

A script to benchmark the v0.0.1 debias function against 
a sample of the MS-COCO dataset and validate the output using LanguageTool.
This version logs all flagged outliers to a JSON file for analysis.
'''
import time
import json
import datasets as ds
import language_tool_python
from nexttext import debias

# --- Configuration ---
SAMPLE_SIZE = 1000  # How many captions to test (can be increased to 1000)
LOG_FILE = "benchmark_v0.0.1_outliers.json"
PERSON_KEYWORDS = [
    "man", "woman", "boy", "girl", "person", "men", "women", 
    "boys", "girls", "people", "he", "she", "him", "her", "kid", "child"
]

# --- Helper Function ---
def contains_person(example):
    """Filter function to find captions containing person-related keywords."""
    caption = example['caption'].lower()
    return any(keyword in caption for keyword in PERSON_KEYWORDS)

# --- Main Benchmark Logic ---
if __name__ == "__main__":
    print("--- Starting nexttext v0.0.1 Benchmark ---")
    
    # 1. Initialize Tools
    print("Initializing LanguageTool...")
    try:
        tool = language_tool_python.LanguageTool('en-US')
    except Exception as e:
        print(f"Error initializing LanguageTool. Please ensure Java is installed.")
        print(f"Error: {e}")
        exit()
        
    # 2. Load and Filter Dataset
    print(f"Streaming dataset and filtering for {SAMPLE_SIZE} person-related captions...")
    start_fetch_time = time.time()
    
    dataset = ds.load_dataset(
        "jxie/coco_captions",
        split="train",
        streaming=True,
    )
    person_dataset = dataset.filter(contains_person)
    
    captions_list = []
    for i, item in enumerate(person_dataset):
        if i >= SAMPLE_SIZE:
            break
        captions_list.append(item['caption'])
    
    fetch_time = time.time() - start_fetch_time
    print(f"Done fetching in {fetch_time:.2f} seconds.")

    # 3. Run Debiasing
    print("Processing captions with nexttext.debias...")
    start_debias_time = time.time()
    debiased_list = debias(captions_list)
    debias_time = time.time() - start_debias_time
    
    # 4. Validate Output and Collect Outliers
    print(f"Validating output... Outliers will be logged to '{LOG_FILE}'")
    error_log = []

    for i, (original, debiased) in enumerate(zip(captions_list, debiased_list)):
        original_errors = tool.check(original)
        debiased_errors = tool.check(debiased)

        if len(debiased_errors) > len(original_errors):
            # Log all new errors found in the debiased version
            new_errors = [
                {
                    "message": e.message,
                    "ruleId": e.ruleId,
                    "context": e.context,
                    "replacements": e.replacements
                } for e in debiased_errors if e not in original_errors
            ]

            error_details = {
                "id": i + 1,
                "original_caption": original,
                "debiased_caption": debiased,
                "errors_found": new_errors
            }
            error_log.append(error_details)
    
    # 5. Write Outliers to JSON Log File
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(error_log, f, ensure_ascii=False, indent=4)
    
    # 6. Print a summary to the screen
    flagged_count = len(error_log)
    error_rate = (flagged_count / SAMPLE_SIZE) * 100
    
    print("\n--- Outlier Summary ---")
    if not error_log:
        print("No grammatical errors were introduced in this sample.")
    else:
        print(f"Found {flagged_count} sentences with new grammatical errors.")
        print("Detailed report saved to benchmark_v0.0.1_outliers.json")
        print("\nFirst 5 outliers:")
        for entry in error_log[:5]:
            print(f"\n[{entry['id']}] Original: {entry['original_caption']}")
            print(f"    Debiased: {entry['debiased_caption']}")
            print(f"    Error:    {entry['errors_found'][0]['message']}")

    print("\n--- Benchmark Complete ---")
    print(f"  Grammatical Error Rate: {error_rate:.2f}%")
    print("---------------------------------")
    
    # The sleep workaround is good practice when streaming
    time.sleep(5) 
    print("Script finished.")
