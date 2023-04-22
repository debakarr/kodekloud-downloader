# KodeKloud Downloader

## Disclaimer
Please read the following disclaimer carefully before using the Downloader CLI Tool.

- The CLI Tool is intended for personal use only. By using this tool, you agree to use it at your own risk and assume full responsibility for any consequences that may arise from its use. The developers and contributors of this tool are not responsible for any damages or losses that may occur from its use.

- The use of this tool to download premium courses is for educational purposes only. You must have the proper authorization or permission from the course provider to access the content legally.

- It is strictly prohibited to distribute or share the downloaded content through any means, including but not limited to uploading to file-sharing platforms, torrent sites, or any other form of digital or physical distribution. Doing so is a violation of copyright laws and may result in legal consequences.

---

## Features

- [x] Download video lessons in selected quality
- [x] Organizes downloaded content in a structured folder hierarchy
- [ ] Download resources (PDFs, etc.) alongside video lessons

---

## Prerequisites

- Python 3.8 or higher
- ffmpeg

<details>
    <summary>How to Install FFmpeg on Linux, Mac, and Windows</summary>

# How to Install FFmpeg on Linux, Mac, and Windows

FFmpeg is a powerful and flexible multimedia processing tool that can handle a wide range of tasks, such as video and audio conversion, streaming, and recording. In this guide, we will show you how to install FFmpeg on Linux, Mac, and Windows operating systems.

## Linux

### Ubuntu and Debian-based distributions

1.  Update the package lists for upgrades and new package installations.

`sudo apt update`

1.  Install FFmpeg using the following command:

`sudo apt install ffmpeg`

### Fedora

1.  Install FFmpeg using the following command:

`sudo dnf install ffmpeg`

### Arch Linux and Manjaro

1.  Install FFmpeg using the following command:

`sudo pacman -S ffmpeg`

## Mac

### Using Homebrew

If you don't have Homebrew installed, you can install it by following the instructions on the [official Homebrew website](https://brew.sh/).

Update Homebrew to ensure you have the latest package information:

`brew update`

1.  Install FFmpeg using the following command:

`brew install ffmpeg`

### Using MacPorts

If you don't have MacPorts installed, you can install it by following the instructions on the [official MacPorts website](https://www.macports.org/install.php).

Update MacPorts to ensure you have the latest package information:

`sudo port selfupdate`

1.  Install FFmpeg using the following command:

`sudo port install ffmpeg`

## Windows

### Using Chocolatey

If you don't have Chocolatey installed, you can install it by following the instructions on the [official Chocolatey website](https://chocolatey.org/install).

Open an elevated Command Prompt (run as Administrator) and install FFmpeg using the following command:

`choco install ffmpeg`

### Using Scoop

If you don't have Scoop installed, you can install it by following the instructions on the [official Scoop website](https://scoop.sh/).

Open a PowerShell terminal and install FFmpeg using the following command:

`scoop install ffmpeg`

After following these steps, FFmpeg should be installed on your system. You can check the installation by running the following command in your terminal or command prompt:

`ffmpeg -version`

This will display the FFmpeg version and build information, confirming that the installation was successful.

</details>



## How to get cookie
- Sign in to kodekloud.com
- Download extension such as [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc/related)
- Download the cookie and save it in some location (You can name it something like `cookie.txt`).

![](/static/cookie-demo.png)

## 💻 Installation

To install kodekloud-downloader, simply run the following command:

```css
pip install -U kodekloud-downloader
```

## 📚 Usage

After installing the package, you can use the `kodekloud dl` command to download shows from the command line.

```css
kodekloud dl --help
Usage: kodekloud dl [OPTIONS] [COURSE_URL]

Options:
  -q, --quality [360p|480p|540p|720p|1080p]
                                  Quality of the video to be downloaded.
  -o, --output-dir TEXT           Output directory where downloaded files will
                                  be store.
  -c, --cookie TEXT               Cookie to download the courses.  [required]
  --help                          Show this message and exit.
```

Here is an example:

### 🔍 Download entire course from list of available course in current folder

```css
kodekloud dl -o . -c /path/to/cookie.txt
+-----+-----------------------------------------------------------------------------+---------+------------------------------------------------------------+
| No. | Name                                                                        | Type    | Categories                                                 |
+-----+-----------------------------------------------------------------------------+---------+------------------------------------------------------------+
| 1   | Ultimate Certified Kubernetes Application Developer (CKAD) Mock Exam Series | Premium | Challenges, Containers, Kubernetes                         |
| 2   | GCP DevOps Project                                                          | Premium | Cloud, GCP                                                 |
| 3   | 12 Factor App                                                               | Premium | Productivity                                               |
| 4   | AZ-305: Microsoft Azure Solutions Architect Expert                          | Premium | Certification, Cloud, Devops                               |
| 5   | Ultimate Certified Kubernetes Administrator (CKA) Mock Exam Series          | Free    | Container Orchestration, Kubernetes, Devops, Certification |
| 6   | AWS Lambda                                                                  | Premium | AWS, Cloud                                                 |
| 7   | Linux Professional Institute LPIC-1 Exam 101                                | Premium | Certification, Linux                                       |
| 8   | Advanced Golang                                                             | Premium | Programming                                                |
| 9   | Prometheus Certified Associate (PCA)                                        | Premium | Certification, Kubernetes, Monitoring                      |
| 10  | GCP Cloud Digital Leader Certification                                      | Premium | Cloud, GCP, Certification                                  |
| 11  | OpenShift 4                                                                 | Premium | Container Orchestration, Devops, Red Hat                   |
| 12  | HashiCorp : Terraform Cloud                                                 | Premium | Cloud, Devops, HashiCorp                                   |
| 13  | ArgoCD                                                                      | Premium | CI/CD, Devops, Kubernetes                                  |
| 14  | Amazon Elastic Container Service (AWS ECS)                                  | Free    | AWS, Devops                                                |
| 15  | Red Hat Certified System Administrator(RHCSA)                               | Premium | Devops, Linux, Red Hat, Certification                      |
| 16  | Open Source for Beginners                                                   | Premium | Productivity                                               |
| 17  | Kustomize                                                                   | Premium | Devops, Kubernetes                                         |
| 18  | DevSecOps – Kubernetes DevOps & Security                                    | Premium | Devops, DevSecOps, Kubernetes                              |
| 19  | AZ-104: Microsoft Azure Administrator                                       | Premium | Cloud, Devops, Certification                               |
| 20  | DevOps Interview Preparation Course                                         | Premium | Devops                                                     |
| 21  | Terraform Challenges                                                        | Free    | Challenges, Devops, IAC                                    |
| 22  | HashiCorp Certified: Consul Associate Certification                         | Premium | Devops, HashiCorp                                          |
| 23  | HashiCorp Certified: Vault Associate Certification                          | Premium | Devops, HashiCorp                                          |
| 24  | Kubernetes Challenges                                                       | Free    | Challenges, Devops                                         |
| 25  | Linux Challenges                                                            | Free    | Challenges, Devops, Linux                                  |
| 26  | HashiCorp Certified: Vault Operations Professional 2022                     | Premium | Container Orchestration, Containers, Devops, HashiCorp     |
| 27  | CKS – Challenges                                                            | Free    | Challenges, Container Orchestration, Containers, Devops    |
| 28  | Linux Foundation Certified System Administrator (LFCS)                      | Premium | Devops, Linux, Certification                               |
| 29  | Jenkins                                                                     | Premium | Automation, CI/CD, Devops                                  |
| 30  | Golang                                                                      | Premium | Devops, Programming                                        |
| 31  | Terraform Associate Certification: HashiCorp Certified                      | Premium | Container Orchestration, Devops, IAC, Certification        |
| 32  | Helm for Beginners                                                          | Premium | Container Orchestration, Containers, Devops                |
| 33  | PCAP – Python Certification Course                                          | Premium | Devops, Programming, Python, Certification                 |
| 34  | Istio Service Mesh                                                          | Premium | Devops                                                     |
| 35  | Jinja2 Basics (Mini Course)                                                 | Free    | Devops                                                     |
| 36  | Certified Kubernetes Security Specialist (CKS)                              | Premium | Container Orchestration, Kubernetes, Devops, Certification |
| 37  | Certified Python Entry-Level Programmer: PCEP-30-02                         | Premium | Devops, Programming, Python, Certification                 |
| 38  | JSON Path Test – Free Course                                                | Free    | Devops                                                     |
| 39  | Docker Certified Associate Exam Course                                      | Premium | Containers, Devops, Certification                          |
| 40  | Terraform Basics Training Course                                            | Premium | Automation, Devops, IAC                                    |
| 41  | CKA Certification Course – Certified Kubernetes Administrator               | Premium | Container Orchestration, Containers, Devops                |
| 42  | Certified Kubernetes Application Developer (CKAD)                           | Premium | Container Orchestration, Kubernetes, Devops, Certification |
| 43  | Kubernetes for the Absolute Beginners – Hands-on Tutorial                   | Premium | Container Orchestration, Containers, Kubernetes, Devops    |
| 44  | Docker Training Course for the Absolute Beginner                            | Premium | Containers, Devops                                         |
| 45  | Chef for the Absolute Beginners                                             | Premium | Automation, Devops                                         |
| 46  | OpenShift 3 for the Absolute Beginners                                      | Premium | Container Orchestration, Containers, Devops                |
| 47  | Ansible Advanced Course                                                     | Premium | Automation, Devops, IAC                                    |
| 48  | Learn Ansible Basics – Beginners Course                                     | Premium | Automation, Devops, IAC                                    |
| 49  | Docker – SWARM | SERVICES | STACKS – Hands-on                               | Premium | Containers, Devops                                         |
| 50  | DevOps Pre-Requisite Course                                                 | Premium | Automation, Devops, IAC                                    |
| 51  | Learning Linux Basics Course & Labs                                         | Premium | Devops, Linux                                              |
| 52  | Shell Scripts for Beginners                                                 | Premium | Devops                                                     |
| 53  | Puppet for the Absolute Beginners Course                                    | Premium | Automation, Devops, IAC                                    |
| 54  | GIT for Beginners                                                           | Premium | Devops, Programming                                        |
+-----+-----------------------------------------------------------------------------+---------+------------------------------------------------------------+
Enter the number of the course you want to select: 35
```

![](static/demo-select-download.gif)
