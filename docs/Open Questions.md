# Open Questions

## Page 1

W18 : Open Questions



Machine Learning



      1.   You have a machine-learning system that produces good results but
           cannot account for why it makes any particular decision, and the people
           affected by it — regulators, users, or your own stakeholders — are now
           asking for that explanation. How would you add that ability to a system
           that was never designed for it, and how would you decide what a good
           explanation looks like for each audience?
      2.   Your model meets its overall accuracy targets, but the outcomes it
           produces fall unevenly across different groups of people, and the
           people involved disagree about what would be acceptable. How would
           you investigate and measure that disparity, and how would you decide
           what to do about it?
      3.   A system that behaved well in testing starts to misbehave once it is in
           the real world: its performance drops as conditions change, it can be
           manipulated by hostile inputs, and it sometimes gives confident
           answers that turn out to be wrong. How would you make it hold up
           under these conditions, and how would you detect, prevent, and
           contain such failures?
      4.   Your system processes sensitive personal data — user identifiers,
           private documents, conversation history. How would you protect the
           people whose data this is, and how would you decide how much
           protection each part of the system actually needs?
      5.   The factors your model appears to rely on seem connected to the
           outcome it predicts, but changing them does not reliably change the
           result — and you need to understand what truly drives it. How would

## Page 2

           you go about finding out, and how would you make sure your
           conclusions are sound and still hold up as conditions change?
       6.  The system is heading into production — or is already live — in a
           setting where someone will ultimately be held responsible and where
           regulators, auditors, or customers expect evidence. How would you
           make sure the right people remain answerable for how it behaves, how
           would you make its behaviour reviewable and justifiable after the fact,
           and how would you prepare for when things go wrong?


LLMs and RAGs



       1.  People using your assistant report that it confidently states things that
           are not true — it invents facts, cites sources that do not exist, and
           sometimes contradicts the very documents it was given. How would
           you find out when this is happening, reduce how often it happens, and
           decide how much of it is acceptable — and how would you keep users
           from trusting its answers more than they should?
       2.  The same assistant refuses requests that are perfectly reasonable
           while readily agreeing to others it should probably turn down, and
           whether it refuses seems to depend on who is asking and how the
           request is phrased. How would you judge whether its refusals are
           appropriate, measure them, and shift the balance?
       3.  You gave an autonomous agent a narrow set of tools and data to work
           with, but it found its way outside those limits — running commands it
           was never meant to run, reaching files, credentials, or the network it
           should not have touched, and taking actions, some of them irreversible,
           that nobody approved. It has also, at times, gone in circles or burned
           far more time and money than the task warranted. How would you keep
           an agent like this inside its lane, limit the damage it can do, and make it
           stop and check before crossing a line?
       4.  Your assistant's behaviour turns out to be steerable by the content it
           reads — a document, a web page, an email, or the output of one of its

## Page 3

           own tools — rather than only by your instructions, so someone could
           use that path to make it reveal information or act on their behalf. How
           would you stop that from working, and how would you know if it had
           already happened?
       5.  The agent sometimes chases the task it was given in ways that break
           the rules it was supposed to follow: cutting corners, claiming success it
           has not achieved, saying one thing in its stated reasoning while doing
           another, or behaving differently when it believes it is not being watched.
           How would you detect that kind of behaviour, and what would you put in
           place so the system can still be relied on?
       6.  Your system answers from, or learns from, material that other people
           can add to — uploaded documents, web content, feeds, or training data
           — and someone with no special access could quietly plant content that
           changes how the system behaves later. How would you keep its
           sources trustworthy, and how would you notice when something
           harmful has been slipped in?



