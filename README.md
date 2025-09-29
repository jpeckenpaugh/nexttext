# nexttext

## Take your text to the next level.

`nexttext` is a lightweight Python toolkit for **neutralizing and re-framing text** to reduce noise, hidden skew, and unwanted artifacts in your AI pipelines.  

It works equally well on **input labels** (human-annotated training data) and **generated labels** (outputs from captioning or classification models), helping you build systems that are more **reliable, consistent, and testable**.

---

## ✨ Features

- 🧹 **Debias** → Neutralize gendered or stereotypical language automatically  
- 🔄 **Rebias** → Reintroduce controlled skew for testing and validation  
- 📊 Works for both **training data** and **model outputs**  
- ⚡ Simple API with no heavy dependencies  
- 🔓 Open-source under a permissive license (MIT)

---

## 📦 Installation

```bash
pip install nexttext
```

---

## 🚀 Quick Start

```python
>>> from nexttext import debias, rebias

>>> labels = [
...   "A man seated at a table talking to a young girl.",
...   "A girl kneeling to receive communion. Her hands are folded in prayer.",
...   "A doctor speaking with his patient while a nurse takes her vitals."
... ]

>>> debias(labels)
[
  "A person seated at a table talking to a child.",
  "A child kneeling to receive communion. Their hands are folded in prayer.",
  "A doctor speaking with a patient while a nurse takes vitals."
]

>>> rebias("A person working on a car.")
"A man working on his car."

>>> rebias("A person holding a baby.")
"A woman holding a baby."

# Round trip: neutralize, then reintroduce skew
>>> rebias(debias(["A woman holding a baby."]))
["A woman holding a baby."]
```

---

## 🛠 Use Cases

- **Training data cleanup** → Reduce bias before it enters your models.  
- **Inference filtering** → Postprocess outputs for safer, more consistent results.  
- **Validation & testing** → Intentionally rebias text to stress-test robustness.  
- **Standardization** → Ensure consistent labels across diverse datasets.  

---

## 🤝 Contributing

Contributions are welcome!  
Please open an [issue](https://github.com/yourname/nexttext/issues) or a [pull request](https://github.com/yourname/nexttext/pulls) to suggest improvements.

---

## 📄 License

`nexttext` is open-source software released under the [MIT License](LICENSE).
