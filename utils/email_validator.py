import dns.resolver
import re

# Disposable email domains (top ~200)
DISPOSABLE_DOMAINS = {
    "tempmail.com", "throwaway.email", "guerrillamail.com", "guerrillamail.net",
    "mailinator.com", "maildrop.cc", "yopmail.com", "trashmail.com", "10minutemail.com",
    "fakeinbox.com", "sharklasers.com", "grr.la", "guerrillamail.info", "guerrillamailblock.com",
    "throwam.com", "temp-mail.org", "tempail.com", "dispostable.com", "mailnesia.com",
    "mailcatch.com", "binkmail.com", "safetymail.info", "filzmail.com", "trashymail.com",
    "tempinbox.com", "armyspy.com", "cuvox.de", "dayrep.com", "einrot.com",
    "fleckens.hu", "gustr.com", "jourrapide.com", "rhyta.com", "superrito.com",
    "teleworm.us", "tempr.email", "trbvm.com", "mohmal.com", "harakirimail.com",
    "discard.email", "discardmail.com", "discardmail.de", "emailondeck.com",
    "getnada.com", "inboxbear.com", "mailsac.com", "nada.email", "spam4.me",
    "tempmail.ninja", "temp-mail.io", "tmpmail.net", "tmpmail.org", "wegwerfemail.de",
    "wegwerfmail.de", "jetable.org", "mytemp.email", "tempmailaddress.com",
    "burnermail.io", "mailnull.com", "spamgourmet.com", "trashmail.me",
    "trashmail.net", "yopmail.fr", "yopmail.net", "cool.fr.nf", "jetable.fr.nf",
    "courriel.fr.nf", "moncourrier.fr.nf", "speed.1s.fr", "nospam.ze.tc",
    "kurzepost.de", "objectmail.com", "proxymail.eu", "rcpt.at", "trash-mail.at",
    "trashmail.at", "trashmail.io", "wegwerfmail.net", "minutemail.com",
    "tempail.com", "tempomail.fr", "ephemail.net", "getairmail.com",
    "mailexpire.com", "mailforspam.com", "mailmoat.com", "mailshell.com",
    "mailzilla.com", "nomail.xl.cx", "nowmymail.com", "spamfree24.org",
    "spaml.com", "uggsrock.com", "mailtemp.info", "mt2015.com",
}

def validate_email_domain(email: str) -> tuple[bool, str]:
    """Validate email domain. Returns (is_valid, error_message)."""
    
    # Basic format check
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, "Invalid email format"
    
    domain = email.split("@")[1].lower()
    
    # Check disposable domains
    if domain in DISPOSABLE_DOMAINS:
        return False, f"Disposable email domains are not allowed"
    
    # Check if domain has MX records (can receive email)
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        if not mx_records:
            return False, "Email domain cannot receive emails"
    except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return False, "Email domain does not exist"
    except dns.resolver.NoAnswer:
        # Some domains use A record instead of MX
        try:
            dns.resolver.resolve(domain, 'A')
        except Exception:
            return False, "Email domain does not exist"
    except Exception:
        # DNS timeout or other issues — allow to pass (don't block on DNS failures)
        pass
    
    return True, ""
