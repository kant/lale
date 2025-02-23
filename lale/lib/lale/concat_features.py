# Copyright 2019 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import lale.helpers
import lale.operators
import numpy as np
import pandas as pd

class ConcatFeaturesImpl():
    """Transformer to concatenate input datasets. 

    This transformer concatenates the input datasets column-wise.

    Examples
    --------
    >>> A = [ [11, 12, 13],
              [21, 22, 23],
              [31, 32, 33] ]
    >>> B = [ [14, 15],
              [24, 25],
              [34, 35] ]
    >>> trainable_cf = ConcatFeatures()
    >>> trained_cf = trainable_cf.fit(X = [A, B])
    >>> trained_cf.transform([A, B])
        [ [11, 12, 13, 14, 15],
          [21, 22, 23, 24, 25],
          [31, 32, 33, 34, 35] ]
    """

    def __init__(self):
        pass

    def transform(self, X):
        """Transform the list of datasets to one single dataset by concatenating column-wise.
        
        Parameters
        ----------
        X : list
            List of datasets to be concatenated.
        
        Returns
        -------
        [type]
            [description]
        """
        np_datasets = []
        #Preprocess the datasets to convert them to 2-d numpy arrays
        for dataset in X:
            if isinstance(dataset, pd.DataFrame) or isinstance(dataset, pd.Series):
                np_dataset = dataset.values
            else:
                np_dataset = dataset
            if hasattr(np_dataset, 'shape'):
                if len(np_dataset.shape) == 1: #To handle numpy column vectors
                    np_dataset = np.reshape(np_dataset, (np_dataset.shape[0], 1))
            np_datasets.append(np_dataset)
            
        result = np.concatenate(np_datasets, axis=1)
        return result

_hyperparams_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'description': 'Hyperparameter schema for the ConcatFeatures operator.\n',
    'allOf': [{
        'description': 'This first object lists all constructor arguments with their types, but omits constraints for conditional hyperparameters.',
        'type': 'object',
        'additionalProperties': False,
        'relevantToOptimizer': [],
        'properties': {}}]}

_input_fit_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'description': 'Input data schema for training the ConcatFeatures operator. As this operator does not actually require training, this is the same as the input schema for making predictions.',
    'type': 'object',
    'required': ['X'],
    'additionalProperties': True,
    'properties': {
        'X': {
            'description': 'Outermost array dimension is over datasets.',
            'type': 'array',
            'items': {
                'description': 'Middle array dimension is over samples (aka rows).',
                'type': 'array',
                'items': {
                    'description': 'Innermost array dimension is over features (aka columns).',
                    'anyOf': [{
                        'type': 'array',
                        'items': {
                            'type': 'number'},
                    }, {
                        'type': 'number'}]}}}}}

_input_predict_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'description': 'Input data schema for making predictions using the ConcatFeatures operator.',
    'type': 'object',
    'required': ['X'],
    'additionalProperties': False,
    'properties': {
        'X': {
            'description': 'Outermost array dimension is over datasets.',
            'type': 'array',
            'items': {
                'description': 'Middle array dimension is over samples (aka rows).',
                'type': 'array',
                'items': {
                    'description': 'Innermost array dimension is over features (aka columns).',
                    'anyOf': [{
                        'type': 'array',
                        'items': {
                            'type': 'number'},
                    }, {
                        'type': 'number'}]}}}}}

_output_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'description': 'Output data schema for transformed data using the ConcatFeatures operator.',
    'type': 'array',
    'items': {
        'type': 'array',
        'items': {
            'type': 'number'}}}

_combined_schemas = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'description': 'Combined schema for expected data and hyperparameters.',
    'documentation_url': 'https://github.com/IBM/lale',
    'type': 'object',
    'tags': {
        'pre': [],
        'op': ['transformer'],
        'post': []},
    'properties': {
        'hyperparams': _hyperparams_schema,
        'input_fit': _input_fit_schema,
        'input_predict': _input_predict_schema,
        'output': _output_schema }}

if (__name__ == '__main__'):
    lale.helpers.validate_is_schema(_combined_schemas)

ConcatFeatures = lale.operators.make_operator(ConcatFeaturesImpl, _combined_schemas)
