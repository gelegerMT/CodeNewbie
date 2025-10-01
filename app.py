from flask import Flask, render_template, request, jsonify
import os
from io import BytesIO
import base64

import pyotp
import qrcode


app = Flask(__name__)


def build_provisioning_uri(secret: str, account_name: str, issuer: str) -> str:
	"""Build an otpauth URI for use in authenticator apps and QR codes."""
	totp = pyotp.TOTP(secret)
	return totp.provisioning_uri(name=account_name or "", issuer_name=issuer or "")


@app.route("/", methods=["GET", "POST"])
def index():
	if request.method == "POST":
		issuer = (request.form.get("issuer") or "").strip()
		account = (request.form.get("account") or "").strip()
		secret = (request.form.get("secret") or "").replace(" ", "").upper().strip()

		# Generate a new secret if none provided
		if not secret:
			secret = pyotp.random_base32()

		uri = build_provisioning_uri(secret, account, issuer)
		totp = pyotp.TOTP(secret)
		code = totp.now()

		# Create QR code PNG and embed as base64 in the page
		qr_img = qrcode.make(uri)
		buffer = BytesIO()
		qr_img.save(buffer, format="PNG")
		buffer.seek(0)
		qr_base64 = base64.b64encode(buffer.read()).decode("ascii")

		return render_template(
			"index.html",
			issuer=issuer,
			account=account,
			secret=secret,
			uri=uri,
			code=code,
			qr_data=qr_base64,
		)

	# GET: prefill page with a freshly generated secret for convenience
	secret = pyotp.random_base32()
	return render_template("index.html", secret=secret)


@app.route("/api/totp", methods=["GET"])
def api_totp():
	"""Return current TOTP code as JSON for a given secret."""
	secret = (request.args.get("secret") or "").replace(" ", "").upper().strip()
	if not secret:
		return jsonify({"error": "secret required"}), 400

	totp = pyotp.TOTP(secret)
	return jsonify({"code": totp.now(), "period": totp.interval})


if __name__ == "__main__":
	port = int(os.environ.get("PORT", "8000"))
	app.run(host="0.0.0.0", port=port, debug=True)

