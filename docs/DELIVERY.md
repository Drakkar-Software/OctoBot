Octobot's versions
====================
# Version structure
## R.D.MA_MI
- R : Octobot's last final release number
- D : development stage
    - 0 for alpha (status)
    - 1 for beta (status)
    - 2 for release candidate
    - 3 for (final) release
- MA : last major release number
- MI : last minor release number

# Long version structure
## R.D.MA_MI-D_LONG
The designations are the same as "Version structure"

The only change is the D_LONG that corresponds to the development stage :
- **alpha** for alpha (status)
- **beta** for beta (status)
- **release** for release candidate

Octobot's versions tag
====================
# Version tag
To create a tag, use `git tag R.D.MA_MI-D_LONG` with the associated version (see *Long version structure*).

Then push this tag with `git-push --tags`.

How to create an Octobot's release
====================
# Minor release or daily release
- Increase the **MI** version number (*R.D.MA_MI*) in :
    - *config/cst.py*   --> MINOR_VERSION
    - *README.md*       --> OctoBot [R.D.MA_MI]
- Update *docs/CHANGELOG.md*
- Create a tag (see *Octobot's versions tag*)

# Major release or weekly release
- Increase the **MA** version number and reset to 0 the **MI** version number (*R.D.MA_MI*) in :
    - *config/cst.py*   --> MINOR_VERSION
    - *README.md*       --> OctoBot [R.D.MA_MI]
- Update *docs/CHANGELOG.md*
- Create a tag (see *Octobot's versions tag*)

# New development stage release
- Change the **D** and **R** according to development stage (*R.D.MA_MI*) in :
    - *config/cst.py*   --> MINOR_VERSION
    - *README.md*       --> OctoBot [R.D.MA_MI]
- Reset the **MA** and **MI** version number (R.D.MA_MI) in :
    - *config/cst.py*   --> MINOR_VERSION
    - *README.md*       --> OctoBot [R.D.MA_MI]
- Update *docs/CHANGELOG.md*
- Create a tag (see *Octobot's versions tag*)
