# Workflow
## Branch-based
Using the feature branch `fea-my-feature` and integration branch `int-bozo`

### Configuring upstream

```sh
git remote add upstream git@github.com:sample/sample.git
git remote -v
```

The output should show your repository as `origin` and
`sample/sample.git` as `upstream`

### Check out the upstream integration branch and push to your repo
This should automatically create it as a tracking branch of `upstream`

```sh
git checkout int-bozo
git push origin int-bozo
```

### Ensure your integration branch is up-to-date with upstream

```sh
git fetch --all
git checkout int-bozo
git merge --ff-only upstream/int-bozo
git push origin int-bozo
```

If you have any errors at this point, stop and contact an experienced
gitter.

### Rebase your work to include updates to the integration branch
#### If your work is already based on int-bozo
```sh
git checkout fea-my-feature 
git rebase upstream/int-bozo
```

#### If your work is based on a different branch (int-angst)
```sh
git checkout fea-my-feature
git rebase --onto int-bozo int-angst fea-my-feature
```

### Rebase Errors
You may encounter merge conflicts. `git status` is your friend and
tells you how to proceed (typically a combination of `git add` and
`git rebase --continue`).


### Rebase Finished, Push to github
Once you complete the rebase (including any adds and continues).

```sh
git push origin fea-my-feature
```

If you have been pushing `fea-my-feature` to your github repo, you
will get an error such as below. If no one else references any part of
your feature branch, then you may run
```sh
git push --force origin fea-my-feature
```
