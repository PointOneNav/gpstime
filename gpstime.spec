Name:           gpstime
Version:        0.3.2
Release:        1%{?dist}
Summary:        LIGO GPS time libraries

License:        GPLv3+
URL:            http://www.ligo.org
# git archive --format zip --prefix gpstime-0.3.2/ --remote=git@git.ligo.org:cds/gpstime.git -o SOURCES/gpstime-0.3.2.zip tags/0.3.2
Source0:       %{name}-%{version}.zip

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python2-setuptools
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_other_pkgversion}-setuptools
BuildRequires:  python%{python3_other_pkgversion}-devel
%{?systemd_requires}
BuildRequires:	systemd

%description
GPS time libraries for LIGO automation software

%package -n     %{name}-services
Summary:        LIGO GPS time libraries service files
Requires:	python%{python3_pkgversion}-%{name}
%description -n %{name}-services
GPS time libraries for LIGO automation software service files

%package -n     python2-%{name}
Summary:        LIGO GPS time libraries
Provides:	gpstime = %{version}-%{release}
Obsoletes:	gpstime <= 0.3.1
%{?python_provide:%python_provide python2-%{name}}
%description -n python2-%{name}
GPS time libraries for LIGO automation software

%package -n     python%{python3_pkgversion}-%{name}
Summary:        LIGO GPS time libraries
Requires:	python%{python3_pkgversion}-dateutil
Requires:	python%{python3_pkgversion}-requests
%{?python_provide:%python_provide python%{python3_pkgversion}-%{name}}
%description -n python%{python3_pkgversion}-%{name}
GPS time libraries for LIGO automation software

%package -n     python%{python3_other_pkgversion}-%{name}
Summary:        LIGO GPS time libraries
Requires:	python%{python3_other_pkgversion}-dateutil
Requires:	python%{python3_other_pkgversion}-requests
%{?python_provide:%python_provide python%{python3_other_pkgversion}-%{name}}
%description -n python%{python3_other_pkgversion}-%{name}
GPS time libraries for LIGO automation software


%prep
%setup -q
#sed -i -e 's/python3/python/' ietf-leap-seconds.service


%build
%py2_build
%py3_other_build
%py3_build


%install
rm -rf $RPM_BUILD_ROOT
%py3_other_install

mv $RPM_BUILD_ROOT%{_bindir}/gpstime $RPM_BUILD_ROOT%{_bindir}/python%{python3_other_pkgversion}-gpstime
mv $RPM_BUILD_ROOT%{_bindir}/ietf-leap-seconds $RPM_BUILD_ROOT%{_bindir}/python%{python3_other_pkgversion}-ietf-leap-seconds

%py3_install

mv $RPM_BUILD_ROOT%{_bindir}/gpstime $RPM_BUILD_ROOT%{_bindir}/python%{python3_pkgversion}-gpstime
mv $RPM_BUILD_ROOT%{_bindir}/ietf-leap-seconds $RPM_BUILD_ROOT%{_bindir}/python%{python3_pkgversion}-ietf-leap-seconds

%py2_install

mkdir -p $RPM_BUILD_ROOT/var/cache/ietf-leap-seconds
touch $RPM_BUILD_ROOT/var/cache/ietf-leap-seconds/leap-seconds.list
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
install -m 0644 ietf-leap-seconds.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 0644 ietf-leap-seconds.timer $RPM_BUILD_ROOT%{_unitdir}/


%post services
%systemd_post ietf-leap-seconds.service
%systemd_post ietf-leap-seconds.timer

%preun services
%systemd_preun ietf-leap-seconds.service
%systemd_preun ietf-leap-seconds.timer

%postun services
%systemd_postun ietf-leap-seconds.service
%systemd_postun ietf-leap-seconds.timer

%files services
%dir /var/cache/ietf-leap-seconds
%ghost /var/cache/ietf-leap-seconds/leap-seconds.list
%{_unitdir}/ietf-leap-seconds.*

%files -n python2-%{name}
%{python2_sitelib}/*
%{_bindir}/gpstime
%{_bindir}/ietf-leap-seconds

%files -n python%{python3_pkgversion}-%{name}
%{python3_sitelib}/*
%{_bindir}/python%{python3_pkgversion}-gpstime
%{_bindir}/python%{python3_pkgversion}-ietf-leap-seconds

%files -n python%{python3_other_pkgversion}-%{name}
%{python3_other_sitelib}/*
%{_bindir}/python%{python3_other_pkgversion}-gpstime
%{_bindir}/python%{python3_other_pkgversion}-ietf-leap-seconds

%changelog
* Thu Mar 28 2019 Michael Thomas <michael.thomas@LIGO.ORG> - 0.3.2-1
- Updates to 0.3.2
- Add missing dependencies

* Thu Nov 29 2018 Michael Thomas <michael.thomas@LIGO.ORG> - 0.3.1-7
- Add python3.6 support

* Tue Nov 6 2018 Michael Thomas <mthomas@ligo-la.caltech.edu> 0.3.1-6
- Remove duplicate installation files

* Tue Nov 6 2018 Michael Thomas <mthomas@ligo-la.caltech.edu> 0.3.1-5
- Fix broken obsoletes/provides

* Fri Oct 26 2018 Michael Thomas <mthomas@ligo-la.caltech.edu> 0.3.1-4
- Update to support python2 and python3

* Thu Jan 25 2018 Michael Thomas <mthomas@ligo-la.caltech.edu> 0.3.1-3
- Change run interval in the timer unit file.

* Wed Jan 24 2018 Michael Thomas <mthomas@ligo-la.caltech.edu> 0.3.1-2
- Ghost the leap second file so that it gets deleted along with the package

* Wed Oct 12 2016 Michael Thomas <mthomas@ligo-la.caltech.edu> 0.1.2-1
- Initial package
