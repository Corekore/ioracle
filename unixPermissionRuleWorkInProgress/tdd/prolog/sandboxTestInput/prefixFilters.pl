profileRule(profile("mobileProcessProfile"),decision("allow"),operation("file-readSTAR"),filters([prefix(preVar("HOME"),postPath("fileForUser"))])).
profileRule(profile("mobileProcessProfile"),decision("allow"),operation("file-readSTAR"),filters([prefix(preVar("HOME"),postPath("impossible/file"))])).

profileRule(profile("mobileProcessProfile"),decision("allow"),operation("file-writeSTAR"),filters([prefix(preVar("HOME"),postPath("fileForUser"))])).
profileRule(profile("mobileProcessProfile"),decision("allow"),operation("file-writeSTAR"),filters([prefix(preVar("HOME"),postPath("impossible/file"))])).
