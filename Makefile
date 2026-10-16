# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Berghaus (Gigoslav) <berghaus.marcel@gmail.com>
# Standard Linux/FHS Makefile for rog-auto-power

pkgname := rog-auto-power
VERSION := 0.1.2

PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
SBINDIR ?= /usr/local/bin
SYSTEMD_USER_DIR ?= $(PREFIX)/lib/systemd/user
APPDIR ?= $(PREFIX)/share/applications
DOCDIR ?= $(PREFIX)/share/doc/$(pkgname)
LICENSEDIR ?= $(PREFIX)/share/licenses/$(pkgname)

.PHONY: all install uninstall check

all:
	@echo "$(pkgname) v$(VERSION) - Run 'make install DESTDIR=...' or './install.sh'"

check:
	python3 -m py_compile auto-power-profile.py
	bash -n rog-gpu-mux-helper
	bash -n install.sh

install:
	install -Dm755 auto-power-profile.py "$(DESTDIR)$(BINDIR)/auto-power-profile.py"
	ln -sf auto-power-profile.py "$(DESTDIR)$(BINDIR)/rog-auto-power"
	install -Dm755 rog-gpu-mux-helper "$(DESTDIR)$(SBINDIR)/rog-gpu-mux-helper"
	sed 's|ExecStart=%h/.local/bin/auto-power-profile.py|ExecStart=$(BINDIR)/auto-power-profile.py|' auto-power-profile.service > auto-power-profile.service.pkg
	install -Dm644 auto-power-profile.service.pkg "$(DESTDIR)$(SYSTEMD_USER_DIR)/auto-power-profile.service"
	rm -f auto-power-profile.service.pkg
	install -Dm644 rog-auto-power.desktop "$(DESTDIR)$(APPDIR)/rog-auto-power.desktop"
	install -Dm644 LICENSE "$(DESTDIR)$(LICENSEDIR)/LICENSE"
	install -Dm644 NOTICE "$(DESTDIR)$(LICENSEDIR)/NOTICE"
	install -Dm644 AUTHORS "$(DESTDIR)$(DOCDIR)/AUTHORS"
	install -Dm644 CHANGELOG.md "$(DESTDIR)$(DOCDIR)/CHANGELOG.md"
	install -Dm644 README.md "$(DESTDIR)$(DOCDIR)/README.md"

uninstall:
	rm -f "$(DESTDIR)$(BINDIR)/auto-power-profile.py"
	rm -f "$(DESTDIR)$(BINDIR)/rog-auto-power"
	rm -f "$(DESTDIR)$(SBINDIR)/rog-gpu-mux-helper"
	rm -f "$(DESTDIR)$(SYSTEMD_USER_DIR)/auto-power-profile.service"
	rm -f "$(DESTDIR)$(APPDIR)/rog-auto-power.desktop"
	rm -rf "$(DESTDIR)$(LICENSEDIR)"
	rm -rf "$(DESTDIR)$(DOCDIR)"
