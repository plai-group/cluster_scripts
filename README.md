# cluster_scripts
This is a repo of scripts various members of the lab have made to submit jobs to the cluster. The scripts are maintained by their respective owners, who should be contacted directly for information about how to use. See readmes within each directory for script-specific information. Warning: most weren't written for public useage, and will likely need to be modified in order to get running on your machine. 

If do you use any of the scripts, please contact me (vaden) after getting it working. I'm curious to know how what difficulies you had getting it set up, and how we can improve the repo to make it easier for others.

## Pullling and updating submodules

Some of these scripts are added as
[submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules). You can clone
these by running

``` bash
git clone --recurse-submodules
```

or if you already cloned, you can do

``` bash
git submodule update --init
```

The aliases below might be useful as they e.g. let you pull any upstream changes
to the submodules.

``` bash
git config alias.sdiff '!'"git diff && git submodule foreach 'git diff'"
git config alias.spush 'push --recurse-submodules=on-demand'
git config alias.supdate 'submodule update --remote --merge'
```

