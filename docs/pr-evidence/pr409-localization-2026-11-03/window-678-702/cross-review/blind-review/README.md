# W72 independent blind review packet

The packet contains an exact copy of the W72 candidate-free input under input/ and the hash-only blind ledger under output/. No primary proposals or blind target strings are included. The blind pass reviewed only the candidate-free input.

Run python3 output/verify_review.py from this directory. PACKET-SHA256SUMS.txt in input/ verifies the copied candidate-free input; SHA256SUMS.txt verifies the complete blind packet.
