#### Last Updated 6/19


# Anyscale 101 Learning Path

Developing scalable AI applications in the cloud is inherently complex. In addition to managing data, algorithms, and code, teams often face the added burden of handling compute infrastructure, DevOps, and distributed systems.

##  Introduction: Why Anyscale?

**Ray**, a fast-growing open-source framework, simplifies this challenge by providing a Python-native API for building scalable and distributed AI Applications. 

That’s where **Anyscale** comes in. The **Anyscale Platform** provides a fully managed, cloud-native environment that makes it easy to develop and scale Ray applications, without the overhead of managing infrastructure.

**The diagram below illustrates how Anyscale supports AI workloads in any environment.** By abstracting away the complexity of compute environments, data formats, and frameworks, Anyscale provides a unified platform that runs seamlessly on any cloud, accelerator, or hardware stack.

![image.png](https://docs.anyscale.com/assets/images/anyscale-b039955af98833e26b57e032e64c5d24.png)

---

## Learning Path Overview and Objectives

The goal of this learning path is to provide an introductory, hands-on experience in building applications on the Anyscale Platform, with a focus on key considerations for developing scalable AI/ML workloads. We’ll begin by exploring the typical interactive development lifecycle on Anyscale Workspaces, then move on to productionizing workflows using Jobs and Services, and finally wrap up with tools for collaboration and organizational management.



### Developing in Anyscale Workspaces
- `101_01_anyscale_intro_workspaces.ipynb` – Introduction to Workspaces  
- `101_02_anyscale_development_intro.ipynb` – Application Development Basics  
- `101_03_anycale_compute_runtime_intro.ipynb` – Compute Environments & Dependencies  
- `101_04_anyscale_storage_options.ipynb` – Storage Options  
- `101_05_anyscale_logging_and_metrics.ipynb` – Debugging, Logging & Monitoring  

### Deploying Pipelines with Jobs
- `101_06_anyscale_intro_jobs.ipynb` – Introduction to Jobs  

### Deploying Applications with Services
- `101_07_anyscale_intro_services.ipynb` – Introduction to Services  

### Collaborating with Your Team
- `101_08_anyscale_collaboration_intro.ipynb` – Sharing and Collaboration  
- `101_09_anyscale_org_setup.ipynb` – Organization Setup & Access Control  



---

## Getting Started

Before diving into the notebooks, please complete the following setup steps:

### 1. **Sign Up for Anyscale**

If you don’t already have an account, register for a free Anyscale account:  
👉 [https://anyscale.com/signup](https://anyscale.com/signup)

Signing in is required to access the platform and work through the exercises.

### 2. Clone the Repository (Optional)

To download and access all notebooks and files, clone this repository:

```
git clone https://github.com/anyscale/enablement-content-june-2025.git
cd enablement-content-june-2025/GettingStarted
```

### 3. Install Ray and the Anyscale CLI (Recommended)
While only lightly covered in this learning path, we recommend installing both Ray and the Anyscale CLI locally. 

You can find installation instructions here:

[Ray Installation Guide](https://docs.ray.io/en/latest/ray-overview/installation.html)  
[Anyscale CLI Setup](https://docs.anyscale.com/reference/quickstart-cli/)



