# Task 5 — Scaling to 5,000 Gig Workers Over a Weekend

## What Breaks First

If we took the app exactly as it stands today and pointed 5,000 gig workers at it over a weekend, the cracks would show up in this order:

**1. The database locks up.**
The app runs on SQLite, which allows only one write at a time. That's fine when I'm the only one testing it, but with hundreds of people hitting "Submit" around the same time, most requests would start queuing up behind each other, and some would fail outright with a "database is locked" error. This would be the very first thing to break, probably within the first hour of real traffic.

**2. Storage fills up or disappears.**
Every audio file is currently saved straight to the app's own disk. Free or low-tier hosting usually gives very little disk space, and on some platforms that storage isn't even permanent — a restart or redeploy can wipe it clean. At an average of a few MB per clip across 5,000 workers, we're easily looking at 10–15 GB of audio by Sunday night. The app would either run out of space mid-weekend or lose already-submitted files without anyone realizing until it's too late.

**3. The app slows to a crawl.**
Right now, when someone submits a file, the app checks it, hashes it, and pulls out its audio properties (duration, sample rate, loudness) all before telling the user it worked. That's fine one submission at a time, but under real load, every single request sits and waits for all of that to finish. Users would see the page hang, assume it failed, and hit submit again — which only adds more load and more duplicate attempts.

**4. Streamlit itself isn't built for this kind of traffic.**
Streamlit is meant for dashboards and small internal tools, not a public form open to thousands of people at once. It runs as a single process, so there's a hard ceiling on how many people can use it at the same time, no matter how good the hosting is.

**5. Bad connections mean lost submissions.**
Gig workers are very likely uploading from mobile data with weak or unstable signal. If an upload drops halfway, there's currently no retry — the person just has to start over. Some won't bother a second time, and we'd never even know they tried.

## What I'd Change Before Launch

**Storage:** Move audio files off the app server entirely and into proper cloud storage (something like S3). This keeps files safe even if the app restarts, and storage can grow independently without touching the app itself.

**Database:** Swap SQLite for a proper multi-user database like Postgres. It's built to handle many people writing at the same time without locking everyone else out.

**Uploads:** Validate the file (type, size, length) on the user's device before it even starts uploading, so we're not wasting bandwidth on files we're going to reject anyway. Ideally also add some retry logic so a dropped connection doesn't force someone to start from zero.

**Failures:** Stop doing all the heavy processing (hashing, extracting audio properties) while the user waits. Instead, save the file and mark it as "pending" immediately, then let that processing happen in the background. The user gets instant confirmation, and processing catches up quietly behind the scenes.

**Duplicates:** Keep the exact-match hash check we already have — it's cheap and works well for someone re-uploading the same file. On top of that, add protection against a shaky connection causing the same button-press to register twice, so a retry doesn't get counted as a second, unrelated submission.

**Cost:** Put a hard cap on file size and recording length before upload even begins, and add basic rate limiting per person so accidental (or intentional) repeated spamming of submissions doesn't quietly run up storage and bandwidth costs over the weekend.

## Bottom Line

The actual logic of the app — matching people to their records, catching duplicates, storing audio details — holds up fine. What wouldn't survive the jump from "a few test uploads" to "5,000 real people in 48 hours" is the plumbing underneath it: a single-writer database, files sitting on the app's own disk, and processing that happens while the user is stuck waiting. Fixing those three things before launch would remove most of the risk; everything else is fine-tuning on top.