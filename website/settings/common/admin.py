SUIT_CONFIG = {
    'ADMIN_NAME': 'sample Admin',

    # Icons: http://getbootstrap.com/2.3.2/base-css.html#icons
    'MENU': (
        # Custom app, with models
        {'label': 'Contact Leads', 'icon': 'icon-pencil', 'models': (
            {'model': 'contacts.contactrequest', 'label': 'All Leads'},
            {'model': 'contacts.contactrequestpartner', 'label': 'Partner Leads'},
            {'model': 'contacts.consultationrequest', 'label': 'Consultation Leads'},
            {'model': 'contacts.contactrequestaboutus', 'label': 'About us Leads'},
            {'model': 'contacts.contactrequestmortgageprofile', 'label': 'Rate-quote Leads'},
            {'model': 'contacts.contactrequestlanding', 'label': 'Landing Leads'},
            {'model': 'contacts.contactrequestlandingextended', 'label': 'Landing Leads (extended)'},
            {'model': 'contacts.notificationreceiver', 'label': 'Notification receivers'},
            {'model': 'contacts.contactrequestmobileprofile', 'label': 'Mobile Profiles'}
        )},

        {'label': 'Rate quote', 'icon': 'icon-check', 'models': (
            'mortgage_profiles.mortgageprofile',
            'mortgage_profiles.mortgageprofilepurchase',
            'mortgage_profiles.mortgageprofilerefinance',
            'mortgage_profiles.rate_quote_request',
        )},

        {'label': 'Loans', 'icon': 'icon-briefcase', 'models': (
            'loans.loan',
            'progress.progressstep',
            'sample_notifications.message',
            'conditions.condition',
        )},

        {'label': 'Loans V1', 'models': (
            'loans.loanv1',
            'loans.loanprofilev1',
            'loans.employmentv1',
            'loans.addressv1',
            'loans.contactv1',
            'loans.borrowerv1',
            'loans.coborrowerv1',
            'loans.holdingassetv1',
            'loans.liabilityv1',
            'loans.vehicleassetv1',
            'loans.insuranceassetv1',
            'loans.incomev1',
            'loans.expensev1',
            'loans.demographicsv1',
        )},

        {'label': 'Users', 'icon': 'icon-user', 'models': (
            {'model': 'accounts.CustomerProtectedProxyModel', 'label': 'Customer'},
            'accounts.advisor',
            'accounts.defaultadvisor',
            'accounts.coordinator',
            'accounts.realtor',
            'accounts.specialist',
            'accounts.user',
            'accounts.phoneverification'
        )},

        'pages',

        {'label': 'Other', 'models': (
            {'model': 'contacts.location', 'label': '[Rate quote] Locations'},
        )},

        {'label': 'Storage', 'models': (
            'storage.storage',
            'storage.document',
            'storage.documentcategory',
            'storage.documentcriteria',
            'storage.documenttag',
            'storage.documenttype'
        )},

        'referral',

        {'label': 'Global Configuration', 'models': (
            {'model': 'core.officeaddress'},
            {'model': 'core.encompasssync'},
            {'model': 'core.recaptcha'},
        )},

        {'label': 'Salesforce', 'models': (
            {'model': 'vendors.salesforceratequoteinfo',
             'label': 'RateQuote Lead'},
            {'model': 'vendors.salesforcesampleonereginfo',
             'label': 'sampleOne Registration Lead'},
        )},
    )
}
