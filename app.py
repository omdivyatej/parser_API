from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import re
import pdfplumber
import tempfile
import os
app = FastAPI()

@app.post("/parse_invoice/")
async def parse_invoice(file: UploadFile | None = None):
    if not file:
        return {"message": "No upload file sent"}
    else:   
        # Ensure the temp directory exists or create it
        temp_dir = os.path.join(os.getcwd(), "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Define the path for the temporary file
        temp_file_path = os.path.join(temp_dir, f"temp_{file.filename}")

        try:
            # Save the uploaded file
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            with pdfplumber.open(temp_file_path) as pdf:
                combined_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:  # Check if any text was extracted to avoid adding None
                        combined_text += text + '\n'
                invoice_details = extract_invoice_details(combined_text, pdf)
                
                return invoice_details
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


def extract_invoice_details(text,pdf):
    try:
        page = pdf.pages[0]
        bounding_box_bill_to_address = (15, 120, 125, 175)   # (left x1, top, right x2, bottom)
        bounding_box_delivery_address= (305, 120, 440, 152)
        billing_address = page.crop(bbox=bounding_box_bill_to_address).extract_text()
        delivery_address = page.crop(bbox=bounding_box_delivery_address).extract_text()
        # Defining regular expressions
        invoice_date_pattern= r"Date (\d{1,2}/\d{1,2}/\d{4})"
        invoice_number_pattern = r"Estimate # (\d+)"
        product_details_pattern = r"^(\d+)\s+(.+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})\s+(\d{1,3}(?:,\d{3})*\.\d{2})$" 
        sales_tax_pattern = r"Sales Tax\s+\$([\d.]+)"
        
        
        invoice_date = re.search(invoice_date_pattern, text)
        if invoice_date:
            invoice_date = invoice_date.group(1)
        # Extracting grouped information using regex
        invoice_number = re.search(invoice_number_pattern, text)
        if invoice_number:
            invoice_number = invoice_number.group(1)
        product_details = re.findall(product_details_pattern, text, re.MULTILINE)
        sales_tax = re.search(sales_tax_pattern, text)
        if sales_tax:
            sales_tax = sales_tax.group(1)
        
        details= {
            "Invoice Number": invoice_number,
            "Invoice Date": invoice_date,  # Not found in the given text
            "Billing Address": billing_address,
            "Delivery Address": delivery_address,
            "Product Details": [
                {
                "QTY": item[0],
                "Description": item[1],
                "Unit Price": item[2],
                "Total Price": item[3],               
                "Confidence": 2, 
                "Category": 3
                }
                for item in product_details
            ],
            "Total Amount": None,  # Not found in the given text
            "Discount": None,  # Not found in the given text
            "Sales Tax": sales_tax,
            "Invoice Total": None  # Not found in the given text
        }
        details["Billing Address"] = billing_address.replace('\n', ' ')
        details["Delivery Address"] = delivery_address.replace('\n', ' ')
        return details
    except Exception as e:
        print(f"Error in extract_invoice_details: {str(e)}")
    

