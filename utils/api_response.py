def api_response(success , statuscode , description):
    return {
        'success' : success ,
        'statuscode' : statuscode,
        'data' : description
    }

