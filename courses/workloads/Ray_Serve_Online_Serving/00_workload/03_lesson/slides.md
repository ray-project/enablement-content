---
theme: seriph
background: /slides_background.png
class: text-center
drawings:
    persist: 
# slide transition: https://sli.dev/guide/animations.html#slide-transitions
# transition: fade
# enable MDC Syntax: https://sli.dev/features/mdc
mdc: true
# duration of the presentation
duration: 15min
addons:
    - fancy-arrow
    - slidev-addon-tldraw
    - slidev-component-spotlight
    - slidev-component-poll
    - slidev-addon-typst
---


# Deploying Our Model and Testing it

---


 ### Deploy the model


serve.run(MySentimentModel.bind()) # Bind the deployment to the Ray Serve runtime


DeploymentHandle(deployment='MySentimentModel')

---

## Simulate Client: Send test requests

We use *requests* library to send HTTP requests to the deployed model.

Note: if you encounter any errors with serve not able to start, most likely it is due to previous instance of serve not being shutdown properly. Restart the notebook or see towards the end of notebook to see how to gracefully shutdown ray serve and the ray cluster.

import requests # used to send HTTP requests to the deployed model


# Query the deployed model
response = requests.get("http://localhost:8000/predict", params={"text": "I love Ray Serve!"})
print(response.json())  # Should print the sentiment analysis result


{'text': 'i love ray serve!', 'sentiment': [{'label': 'POSITIVE', 'score': 0.9998507499694824}]}


---

```python
text = "Mars landscape is a tough place to live, but it has its own beauty. Venus is even tougher, with its extreme heat and pressure. "
response = requests.get("http://localhost:8000/predict", params={"text": text})
print(response.json())  # prints result, note the text is truncated to 50 characters in the application logic

{'text': 'mars landscape is a tough place to live, but it ha', 'sentiment': [{'label': 'NEGATIVE', 'score': 0.9590334296226501}]}

```

---

```python
text = "National Parks are a great way to experience nature and wildlife."
response = requests.get("http://localhost:8000/predict", params={"text": text})
print(response.json())  # # prints result, note the text is truncated to 50 characters in the application logic

{'text': 'national parks are a great way to experience natur', 'sentiment': [{'label': 'POSITIVE', 'score': 0.9996353387832642}]}

```