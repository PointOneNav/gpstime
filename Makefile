NAME=gpstime
VERSION=0.4.4

sources:
	git archive --format zip --prefix $(NAME)-$(VERSION)/ -o $(NAME)-$(VERSION).zip tags/$(VERSION)
	rpmbuild -D '_srcrpmdir ./' -D '_sourcedir ./' -bs gpstime.spec
