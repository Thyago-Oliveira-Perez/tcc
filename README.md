# Collecting Commit Data from the Kubernetes Project

This project aims to collect and analyze the number of commits in the Kubernetes repository. The project categorizes commits into two main categories: **refactor commits** and **fix commits**.

### Classification Criteria

- **Refactor Commits**: Commit messages that contain words like `refact`, `refactor`, `rewrite`, `improve`, `remake`, or `recode` will be classified as refactor commits.
- **Fix Commits**: If the commit message includes terms like `fix`, `hotfix`, `resolve`, or `solve`, it will be considered a fix commit.

The purpose of this analysis is to understand the frequency and proportion of each type of commit in the development of Kubernetes.

## References

- [Kubernetes project](https://github.com/kubernetes/kubernetes)
